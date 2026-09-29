"""Invoice filtering and query budgets against an isolated in-memory database."""
import unittest
from datetime import date
from sqlalchemy import event
from tests import test_mobile_api
from pear_admin.extensions import db
from pear_admin.orms import MaterialInvoiceORM, MaterialInvoiceDetailORM, ProjectORM, SupplierORM


class InvoiceSearchTest(unittest.TestCase):
    setUp = test_mobile_api.MobileAPITest.setUp
    tearDown = test_mobile_api.MobileAPITest.tearDown

    def seed(self):
        for i in range(24):
            project = ProjectORM(project_name=f'项目{i}')
            supplier = SupplierORM(name=f'供应商{i}', type_id=1, contact_person='联系人', phone='', bank_name='', account_number='')
            invoice = MaterialInvoiceORM(invoice_number=f'TEST_{i:03d}', invoice_date=date(2026, 9, 28),
                buyer_name='测试园林公司', seller_name='苗木公司' if i % 2 else '建材公司',
                invoice_category='plants' if i % 2 else 'material', project=project, supplier=supplier)
            invoice.details.append(MaterialInvoiceDetailORM(name='测试材料', quantity=2, price=10, amount=20, tax_amount=2.6))
            db.session.add(invoice)
        db.session.commit()
        db.session.remove()

    def get(self, **params):
        result = self.client.get('/api/v1/material/invoice', query_string=params, headers=self.headers)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['code'], 0, result.json)
        return result.json

    def test_category_and_partial_names_filter_before_paging(self):
        self.seed()
        first = self.get(invoice_category='plants', buyer_name=' 园林 ', seller_name='苗', page=1, limit=5)
        second = self.get(invoice_category='plants', buyer_name='园林', seller_name='苗', page=2, limit=5)
        self.assertEqual(first['count'], 12)
        self.assertEqual(len(first['data']), 5)
        self.assertTrue(all(row['invoice_category'] == 'plants' for row in first['data']))
        self.assertFalse({r['id'] for r in first['data']} & {r['id'] for r in second['data']})
        self.assertEqual(self.get(invoice_number='023')['count'], 1)
        self.assertEqual(self.get(seller_name='不存在')['count'], 0)

    def test_search_treats_percent_and_underscore_as_literal_text(self):
        self.seed()
        self.assertEqual(self.get(invoice_number='%')['count'], 0)
        self.assertEqual(self.get(search='_')['count'], 24)
        self.assertEqual(self.get(invoice_number='TEST_0')['count'], 24)

    def test_payment_options_match_raw_supplier_name_only_and_skip_invoice_details(self):
        supplier = SupplierORM(name='杭州雅鸿装饰工程有限公司', type_id=1,
            contact_person='钱顺怡', phone='', bank_name='', account_number='')
        db.session.add(supplier)
        db.session.flush()
        sid = supplier.id
        for number, seller, buyer in [
            ('MATCH-1', supplier.name, '购买公司'),
            ('MATCH-2', supplier.name, '购买公司'),
            ('CONTACT', supplier.contact_person, '购买公司'),
            ('COMBINED', supplier.name + '（钱顺怡）', '购买公司'),
            ('PARTIAL', '杭州雅鸿装饰工程有限公司分公司', '购买公司'),
            ('BUYER', '无关公司', supplier.name),
        ]:
            db.session.add(MaterialInvoiceORM(invoice_number=number, seller_name=seller,
                buyer_name=buyer, total_amount=100, tax_amount=13, ocr_result='large OCR payload'))
        db.session.commit()
        db.session.remove()
        queries = []
        def track(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith('SELECT'):
                queries.append(statement)
        event.listen(db.engine, 'before_cursor_execute', track)
        try:
            result = self.get(mode='payment_options', payee_supplier_id=sid, limit=1)
        finally:
            event.remove(db.engine, 'before_cursor_execute', track)
        self.assertEqual(result['count'], 2)
        self.assertEqual([r['invoice_number'] for r in result['data']], ['MATCH-2'])
        self.assertEqual(float(result['data'][0]['total_amount']), 100)
        self.assertEqual(float(result['data'][0]['tax_amount']), 13)
        self.assertNotIn('details', result['data'][0])
        self.assertNotIn('ocr_result', result['data'][0])
        self.assertNotIn('file_url', result['data'][0])
        self.assertFalse(any('material_invoice_detail' in sql or 'ocr_result' in sql for sql in queries))
        self.assertLessEqual(len(queries), 4)
        second = self.get(mode='payment_options', payee_supplier_id=sid, limit=1, page=2)
        self.assertEqual([r['invoice_number'] for r in second['data']], ['MATCH-1'])
        for invalid in (None, '', 'invalid', 999999):
            self.assertEqual(self.get(mode='payment_options', payee_supplier_id=invalid)['count'], 0)

    def test_payment_options_remove_trailing_contact_from_stored_supplier_name(self):
        supplier = SupplierORM(name='杭州雅鸿装饰工程有限公司（钱顺怡）', type_id=1,
            contact_person='钱顺怡', phone='', bank_name='', account_number='')
        db.session.add(supplier)
        db.session.add_all([
            MaterialInvoiceORM(invoice_number='MATCH', seller_name='杭州雅鸿装饰工程有限公司'),
            MaterialInvoiceORM(invoice_number='COMBINED', seller_name=supplier.name),
            MaterialInvoiceORM(invoice_number='PARTIAL', seller_name='杭州雅鸿装饰工程有限公司分公司'),
        ])
        db.session.commit()
        for stored_name in ('杭州雅鸿装饰工程有限公司（钱顺怡）', '杭州雅鸿装饰工程有限公司 ( 钱顺怡 ) '):
            supplier.name = stored_name
            db.session.commit()
            result = self.get(mode='payment_options', payee_supplier_id=supplier.id)
            self.assertEqual([r['invoice_number'] for r in result['data']], ['MATCH'])
            self.assertEqual(supplier.name, stored_name)

    def test_payment_options_preserve_parentheses_belonging_to_company_name(self):
        supplier = SupplierORM(name='雅鸿（杭州）装饰工程有限公司（钱顺怡）', type_id=1,
            contact_person='钱顺怡', phone='', bank_name='', account_number='')
        db.session.add(supplier)
        db.session.add_all([
            MaterialInvoiceORM(invoice_number='MATCH', seller_name='雅鸿（杭州）装饰工程有限公司'),
            MaterialInvoiceORM(invoice_number='WRONG', seller_name='雅鸿装饰工程有限公司'),
        ])
        db.session.commit()
        result = self.get(mode='payment_options', payee_supplier_id=supplier.id)
        self.assertEqual([r['invoice_number'] for r in result['data']], ['MATCH'])

    def test_query_count_does_not_grow_per_invoice(self):
        self.seed()
        def measured(limit):
            db.session.remove()
            queries = []
            def track(conn, cursor, statement, parameters, context, executemany):
                if statement.lstrip().upper().startswith('SELECT'):
                    queries.append(statement)
            event.listen(db.engine, 'before_cursor_execute', track)
            try:
                result = self.get(limit=limit)
            finally:
                event.remove(db.engine, 'before_cursor_execute', track)
            self.assertTrue(all(r['details'][0]['name'] == '测试材料' for r in result['data']))
            return len(queries)
        one = measured(1)
        twenty = measured(20)
        self.assertLessEqual(twenty, one + 1)
        self.assertLessEqual(twenty, 10)


if __name__ == '__main__':
    unittest.main()
