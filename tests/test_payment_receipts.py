"""Receipt collection and explicit links, using an offline disposable database."""
import unittest
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pymupdf

from pear_admin.extensions import db
from pear_admin.orms import PayORM, SupplierORM, PayerORM, OrderORM, MaterialInvoiceORM, PaymentReceiptORM
from tests import test_mobile_api


class PaymentReceiptsTest(unittest.TestCase):
    setUp = test_mobile_api.MobileAPITest.setUp
    tearDown = test_mobile_api.MobileAPITest.tearDown
    base = '/api/v1/payment-receipts'

    def upload(self, suffix='pdf', content=None):
        if content is None:
            with pymupdf.open() as doc:
                doc.new_page().insert_text((40, 50), 'Bank payment receipt')
                content = doc.tobytes()
        return self.client.post(self.base + '/upload', headers=self.headers,
                                data={'file': (BytesIO(content), '银行回单.' + suffix)})

    def receipt(self):
        response = self.upload()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['code'], 0)
        return response.json['data']

    def seed_payments(self):
        supplier = SupplierORM(type_id=1, name='测试园林有限公司', contact_person='张先生',
                               phone='', bank_name='', account_number='')
        payer = PayerORM(type_id=1, name='付款公司')
        invoice = MaterialInvoiceORM(invoice_number='KEEP')
        db.session.add_all([supplier, payer, invoice]); db.session.flush()
        order = OrderORM(order_number='ORDER-001', supplier_id=supplier.id, material_name='苗木')
        db.session.add(order); db.session.flush()
        payments = [PayORM(pay_number=f'PAY-{i}', order_id=order.id,
                           payee_supplier_id=supplier.id, payer_supplier_id=payer.id,
                           current_payment_amount='120.50') for i in range(2)]
        payments[0].invoices.append(invoice)
        db.session.add_all(payments); db.session.commit()
        return [pay.id for pay in payments], invoice.id

    def test_upload_edit_search_and_pdf_preview(self):
        row = self.receipt()
        self.assertEqual(row['file_type'], 'pdf')
        self.assertEqual(row['file_name'], '银行回单.pdf')
        self.assertEqual(row['payments'], [])
        changed = self.client.put(f"{self.base}/{row['id']}", headers=self.headers, json={
            'receipt_number': 'BANK-001', 'payment_date': '2026-10-04',
            'payer_name': '付款公司', 'payee_name': '测试园林有限公司',
            'amount': '120.50', 'bank_name': '测试银行', 'remarks': '苗木款',
            'file_path': '/uploads/forged.pdf',
        }).json
        self.assertEqual(changed['code'], 0)
        self.assertEqual(changed['data']['amount'], '120.50')
        self.assertEqual(changed['data']['file_path'], row['file_path'])
        found = self.client.get(self.base + '?q=BANK-001&linked=unlinked', headers=self.headers).json
        self.assertEqual(found['count'], 1)
        self.assertEqual(found['data'][0]['receipt_number'], 'BANK-001')
        preview = self.client.get(f"{self.base}/{row['id']}/preview-page?page=1", headers=self.headers)
        self.assertEqual(preview.status_code, 200)
        self.assertTrue(preview.json['data']['image'].startswith('data:image/png;base64,'))
        self.assertIn('no-store', preview.headers['Cache-Control'])

    def test_append_links_preserves_invoices_and_unlinks_only_selected_payment(self):
        row = self.receipt()
        ids, invoice_id = self.seed_payments()
        endpoint = f"{self.base}/{row['id']}/payments"
        for selected in ([ids[0]], [ids[1]], [ids[1]]):
            linked = self.client.post(endpoint, headers=self.headers, json={'payment_ids': selected})
            self.assertEqual(linked.json['code'], 0)
        self.assertEqual({pay['id'] for pay in linked.json['data']['linked']}, set(ids))
        self.assertEqual([inv.id for inv in db.session.get(PayORM, ids[0]).invoices], [invoice_id])
        reverse = self.client.get(self.base + f'?payment_id={ids[0]}', headers=self.headers).json
        self.assertEqual(reverse['count'], 1)
        self.client.delete(endpoint + f'/{ids[0]}', headers=self.headers)
        remaining = self.client.get(endpoint, headers=self.headers).json['data']['linked']
        self.assertEqual([pay['id'] for pay in remaining], [ids[1]])
        removed = self.client.delete(f"{self.base}/{row['id']}", headers=self.headers)
        self.assertEqual(removed.json['code'], 0)
        self.assertIsNotNone(db.session.get(PayORM, ids[0]))
        self.assertIsNotNone(db.session.get(PayORM, ids[1]))
        self.assertTrue((Path(self.temp.name) / row['file_path'].removeprefix('/uploads/')).is_file())

    def test_invalid_links_and_metadata_are_atomic(self):
        row = self.receipt()
        ids, _ = self.seed_payments()
        endpoint = f"{self.base}/{row['id']}/payments"
        self.client.post(endpoint, headers=self.headers, json={'payment_ids': [ids[0]]})
        for values in ([ids[1], 99999], [True], '1', None):
            response = self.client.post(endpoint, headers=self.headers, json={'payment_ids': values})
            self.assertNotEqual(response.json['code'], 0)
        self.assertEqual([p['id'] for p in self.client.get(endpoint, headers=self.headers).json['data']['linked']], [ids[0]])
        for bad in ({'amount': 'NaN'}, {'amount': '-1'}, {'amount': '0.001'},
                    {'amount': '10000000000000000'}, {'payment_date': '2026-02-30'}):
            result = self.client.put(f"{self.base}/{row['id']}", headers=self.headers,
                                     json={'remarks': 'must roll back', **bad}).json
            self.assertNotEqual(result['code'], 0)
        fresh = self.client.get(f"{self.base}/{row['id']}", headers=self.headers).json['data']
        self.assertEqual(fresh['remarks'], '')

    def test_duplicate_file_reuses_saved_receipt_and_rejects_invalid_files(self):
        with pymupdf.open() as doc:
            doc.new_page()
            content = doc.tobytes()
        response = self.upload(content=content)
        self.assertEqual(response.status_code, 200)
        first = response.json['data']
        second = self.upload(content=content).json['data']
        self.assertEqual(first['id'], second['id'])
        self.assertTrue(second['reused'])
        self.assertEqual(self.client.get(self.base, headers=self.headers).json['count'], 1)
        for ext, data in (('exe', b'MZ'), ('pdf', b'not a pdf'), ('png', b'not an image')):
            self.assertNotEqual(self.upload(ext, data).json['code'], 0)

    def test_candidate_search_and_pagination(self):
        row = self.receipt()
        ids, _ = self.seed_payments()
        candidates = self.client.get(f"{self.base}/{row['id']}/payments?q=PAY-1", headers=self.headers).json
        self.assertEqual([p['id'] for p in candidates['data']['candidates']], [ids[1]])
        self.assertEqual(candidates['data']['linked'], [])
        self.client.post(f"{self.base}/{row['id']}/payments", headers=self.headers, json={'payment_ids': [ids[0]]})
        self.assertEqual(self.client.get(self.base + '?linked=unlinked', headers=self.headers).json['count'], 0)
        self.assertEqual(self.client.get(self.base + '?linked=linked', headers=self.headers).json['count'], 1)

    def test_authentication_required_for_collection_and_preview(self):
        row = self.receipt()
        for endpoint in (self.base, f"{self.base}/{row['id']}", f"{self.base}/{row['id']}/preview-page"):
            self.assertIn(self.client.get(endpoint).status_code, (401, 403))

    def seed_receipts(self, count=1):
        rows = [PaymentReceiptORM(receipt_number=f'BANK-{i:03}', payer_name='付款公司',
                                  payee_name='测试园林有限公司', bank_name='测试银行',
                                  remarks='苗木款', file_name=f'银行回单-{i:03}.pdf',
                                  file_path=f'/uploads/receipt-{i:03}.pdf', file_type='pdf',
                                  file_size=10, file_hash=f'{i:064x}') for i in range(count)]
        db.session.add_all(rows)
        db.session.commit()
        return [row.id for row in rows]

    def test_payment_receipt_append_preserves_previous_links_and_business_data(self):
        ids, invoice_id = self.seed_payments()
        receipt_ids = self.seed_receipts(3)
        pay = db.session.get(PayORM, ids[0])
        pay.payment_purpose = '已核验的苗木款'
        pay.current_payment_amount = Decimal('120.50')
        pay.invoice_amount = Decimal('100.00')
        pay.payment_status = '已支付'
        pay.handler = '原经办人'
        pay.attachments = '[{"name":"原附件.pdf","url":"/uploads/original.pdf"}]'
        pay.generated_at = datetime(2026, 10, 4, 10, 30)
        pay.created_by_id = 11
        pay.created_by_nickname = '原创建人'
        pay.updated_at = datetime(2026, 10, 4, 11, 30)
        pay.updated_by_id = 12
        pay.updated_by_nickname = '原修改人'
        pay.payment_receipts.append(db.session.get(PaymentReceiptORM, receipt_ids[0]))
        shared = db.session.get(PaymentReceiptORM, receipt_ids[1])
        shared.payments.append(db.session.get(PayORM, ids[1]))
        db.session.commit()
        before = {column.key: getattr(pay, column.key) for column in PayORM.__table__.columns}
        endpoint = f'{self.base}/for-payment/{ids[0]}'
        for selected in ([receipt_ids[1], receipt_ids[2]], receipt_ids, [receipt_ids[1], receipt_ids[1]]):
            response = self.client.post(endpoint, headers=self.headers, json={'receipt_ids': selected})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['code'], 0, response.json)
            self.assertEqual(response.json['data']['payment']['id'], ids[0])
            self.assertEqual(response.json['data']['payment']['current_payment_amount'], '120.50')
            self.assertEqual(response.json['data']['payment']['payee_supplier_name'], '测试园林有限公司')
            self.assertEqual({row['id'] for row in response.json['data']['linked']}, set(receipt_ids))
            self.assertEqual(response.json['data']['count'], 0)
        db.session.expire_all()
        saved = db.session.get(PayORM, ids[0])
        self.assertEqual({column.key: getattr(saved, column.key) for column in PayORM.__table__.columns}, before)
        self.assertEqual([invoice.id for invoice in saved.invoices], [invoice_id])
        self.assertEqual({p.id for p in db.session.get(PaymentReceiptORM, receipt_ids[1]).payments}, set(ids))
        # Both association directions can append the same pair without duplication.
        reverse = self.client.post(f'{self.base}/{receipt_ids[1]}/payments', headers=self.headers,
                                   json={'payment_ids': [ids[0]]})
        self.assertEqual(reverse.json['code'], 0)
        self.assertEqual({row['id'] for row in self.client.get(endpoint, headers=self.headers).json['data']['linked']}, set(receipt_ids))

    def test_payment_receipt_invalid_selection_is_atomic_and_requires_authentication(self):
        ids, _ = self.seed_payments()
        receipt_ids = self.seed_receipts(2)
        endpoint = f'{self.base}/for-payment/{ids[0]}'
        linked = self.client.post(endpoint, headers=self.headers, json={'receipt_ids': [receipt_ids[0]]})
        self.assertEqual(linked.status_code, 200)
        self.assertEqual(linked.json['code'], 0)
        for values in ([receipt_ids[1], 99999], [True], '1', None, [-1], [0], [1.5]):
            with self.subTest(values=values):
                response = self.client.post(endpoint, headers=self.headers, json={'receipt_ids': values})
                self.assertEqual(response.json['code'], -1)
                self.assertEqual([row['id'] for row in self.client.get(endpoint, headers=self.headers).json['data']['linked']], [receipt_ids[0]])
        empty = self.client.post(endpoint, headers=self.headers, json={'receipt_ids': []})
        self.assertEqual(empty.json['code'], 0)
        for method in ('get', 'post'):
            request = getattr(self.client, method)
            self.assertIn(request(endpoint).status_code, (401, 403))
            missing = request(f'{self.base}/for-payment/99999', headers=self.headers,
                              json={'receipt_ids': [receipt_ids[1]]})
            self.assertEqual(missing.json['code'], -1)
            self.assertIn('付款单', missing.json['msg'])

    def test_payment_receipt_candidates_search_pagination_and_recommendation(self):
        ids, _ = self.seed_payments()
        receipt_ids = self.seed_receipts(24)
        linked_receipt = db.session.get(PaymentReceiptORM, receipt_ids[0])
        linked_receipt.payments.append(db.session.get(PayORM, ids[0]))
        shared_receipt = db.session.get(PaymentReceiptORM, receipt_ids[1])
        shared_receipt.payments.append(db.session.get(PayORM, ids[1]))
        unrelated_receipt = db.session.get(PaymentReceiptORM, receipt_ids[2])
        unrelated_receipt.payee_name = '无关建筑有限公司'
        db.session.commit()
        endpoint = f'{self.base}/for-payment/{ids[0]}'
        first = self.client.get(endpoint, headers=self.headers)
        self.assertEqual(first.status_code, 200)
        data = first.json['data']
        self.assertEqual(data['payment']['id'], ids[0])
        self.assertEqual(data['payment']['current_payment_amount'], '120.50')
        self.assertEqual(data['payment']['payee_supplier_name'], '测试园林有限公司')
        self.assertEqual([row['id'] for row in data['linked']], [receipt_ids[0]])
        self.assertEqual(data['count'], 23)
        self.assertEqual(len(data['candidates']), 20)
        self.assertTrue(all(row['recommended'] for row in data['candidates']))
        self.assertEqual(data['candidates'][0]['file_name'], '银行回单-023.pdf')
        second = self.client.get(endpoint + '?page=2', headers=self.headers).json['data']
        self.assertEqual(second['count'], 23)
        self.assertEqual([row['id'] for row in second['candidates']], receipt_ids[1:4][::-1])
        self.assertFalse(next(row for row in second['candidates'] if row['id'] == receipt_ids[2])['recommended'])
        shared = next(row for row in second['candidates'] if row['id'] == receipt_ids[1])
        self.assertEqual([payment['id'] for payment in shared['payments']], [ids[1]])
        for term, expected_count in [('BANK-001', 1), ('无关建筑', 1), ('银行回单-023', 1),
                                     ('测试银行', 23), ('苗木款', 23), ('付款公司', 23), ('BANK-000', 0), ('%', 0)]:
            with self.subTest(term=term):
                result = self.client.get(endpoint, headers=self.headers, query_string={'q': term}).json['data']
                self.assertEqual(result['count'], expected_count)
                self.assertEqual([row['id'] for row in result['linked']], [receipt_ids[0]])
        self.assertEqual(self.client.get(endpoint + '?page=99', headers=self.headers).json['data']['candidates'], [])
