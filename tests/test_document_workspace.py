"""Workspace paging and query-budget regressions, using an isolated database."""
import unittest
from decimal import Decimal
from sqlalchemy import event
from tests import test_mobile_api
from pear_admin.extensions import db
from pear_admin.orms import OrderORM, PayORM, ProjectORM, SupplierORM, PayerORM


class DocumentWorkspaceTest(unittest.TestCase):
    setUp = test_mobile_api.MobileAPITest.setUp
    tearDown = test_mobile_api.MobileAPITest.tearDown

    def seed(self, count=80):
        project = ProjectORM(project_name='项目甲')
        payer = PayerORM(name='付款单位', type_id=1)
        db.session.add_all([project, payer]); db.session.flush()
        self.project_id = project.id
        for i in range(count):
            supplier = SupplierORM(name=f'供应商{i}', contact_person=f'联系人{i}',
                                   type_id=1, phone='', bank_name='测试银行', account_number=str(i))
            db.session.add(supplier); db.session.flush()
            order = OrderORM(order_number=f'D{i:04}', material_name='材料', project_id=project.id,
                             supplier_id=supplier.id, supplier_contact_person=f'联系人{i}', order_amount=100)
            db.session.add(order); db.session.flush()
            db.session.add(PayORM(pay_number=f'F{i:04}', order_id=order.id, payer_supplier_id=payer.id,
                                 payee_supplier_id=supplier.id, current_payment_amount=100 if i == 0 else 25,
                                 invoice_amount=10, payment_status='paid'))
        db.session.commit(); db.session.remove()

    def measured(self, path):
        db.session.remove()
        queries = []
        def track(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith('SELECT'):
                queries.append(statement)
        event.listen(db.engine, 'before_cursor_execute', track)
        try:
            response = self.client.get(path, headers=self.headers)
        finally:
            event.remove(db.engine, 'before_cursor_execute', track)
        return response, len(queries)

    def test_paged_cards_have_bounded_queries_and_complete_totals(self):
        self.seed()
        for kind in ('orders', 'payments'):
            with self.subTest(kind=kind):
                response, queries = self.measured(f'/api/v1/workspace/{kind}?limit=20')
                self.assertEqual(response.status_code, 200)
                data = response.json
                self.assertEqual(data['count'], 80)
                self.assertEqual(len(data['data']), 20)
                self.assertEqual(len(data['contacts']), 80)
                self.assertEqual(Decimal(data['totals']['paid']), Decimal('2075'))
                self.assertLessEqual(queries, 16, f'{kind} executed {queries} SELECTs')
                _, one_queries = self.measured(f'/api/v1/workspace/{kind}?limit=1')
                self.assertLessEqual(queries, one_queries + 1)
                second = self.client.get(f'/api/v1/workspace/{kind}?limit=20&page=2', headers=self.headers).json
                self.assertFalse({r['id'] for r in data['data']} & {r['id'] for r in second['data']})
                if kind == 'payments':
                    self.assertEqual(data['data'][0]['order_summary']['paid_amount'], '25.00')
                    self.assertEqual(data['data'][0]['payee_account']['bank_name'], '测试银行')

    def test_exact_filters_totals_and_hide_settled(self):
        self.seed()
        path = f'/api/v1/workspace/orders?project_id={self.project_id}&supplier_contact_person=联系人1'
        result = self.client.get(path, headers=self.headers)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['count'], 1)
        self.assertEqual(Decimal(result.json['totals']['orders']), Decimal('100'))
        hidden = self.client.get('/api/v1/workspace/orders?hide_settled=1', headers=self.headers).json
        self.assertEqual(hidden['count'], 79)
        self.assertEqual(Decimal(hidden['totals']['orders']), Decimal('8000'))
        payment = self.client.get('/api/v1/workspace/payments?order_number=D0001&payment_status=paid', headers=self.headers).json
        self.assertEqual(payment['count'], 1)
        self.assertEqual(payment['data'][0]['pay_number'], 'F0001')
        literal = self.client.get('/api/v1/workspace/orders?order_number=%25', headers=self.headers).json
        self.assertEqual(literal['count'], 0)

    def test_unlinked_payments_empty_pages_and_auth(self):
        db.session.add(PayORM(pay_number='unlinked', current_payment_amount=10)); db.session.commit()
        response = self.client.get('/api/v1/workspace/payments', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['data'][0]['order_summary'], {})
        empty = self.client.get('/api/v1/workspace/payments?pay_number=absent', headers=self.headers).json
        self.assertEqual(empty['count'], 0)
        self.assertEqual(Decimal(empty['totals']['paid']), 0)
        for kind in ('orders', 'payments'):
            self.assertIn(self.client.get(f'/api/v1/workspace/{kind}').status_code, (401, 403))

    def test_export_paging_caps_payload_without_losing_records(self):
        self.seed(230)
        for kind in ('orders', 'payments'):
            seen = set()
            for page, expected in ((1, 100), (2, 100), (3, 30)):
                result = self.client.get(f'/api/v1/workspace/{kind}?limit=500&page={page}', headers=self.headers).json
                self.assertEqual(result['count'], 230)
                self.assertEqual(len(result['data']), expected)
                ids = {row['id'] for row in result['data']}
                self.assertFalse(seen & ids)
                seen.update(ids)
            self.assertEqual(len(seen), 230)

    def test_split_payments_refunds_and_invoices_are_preserved(self):
        from pear_admin.orms.material import MaterialInvoiceORM
        self.seed(1)
        order = db.session.scalar(db.select(OrderORM))
        payment = db.session.scalar(db.select(PayORM))
        payment.invoices.append(MaterialInvoiceORM(invoice_number='INV1', total_amount=100))
        db.session.add_all([PayORM(pay_number='split', order_id=order.id, current_payment_amount=Decimal('30.10')),
                            PayORM(pay_number='refund', order_id=order.id, current_payment_amount=Decimal('-5.05'))])
        db.session.commit(); db.session.remove()
        result = self.client.get('/api/v1/workspace/orders', headers=self.headers).json
        self.assertEqual(result['totals']['paid'], '125.05')
        self.assertEqual(result['data'][0]['order_balance'], '-25.05')
        self.assertEqual(len(result['data'][0]['pays_list']), 3)
        result = self.client.get('/api/v1/workspace/payments?pay_number=F0000', headers=self.headers).json
        self.assertEqual(result['totals']['paid'], '100.00')
        self.assertEqual(result['data'][0]['order_summary']['paid_amount'], '125.05')
        self.assertEqual(result['data'][0]['invoices_list'][0]['invoice_number'], 'INV1')
