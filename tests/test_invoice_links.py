"""Both entry points share real stored links; no production DB/network involved."""
import unittest
from tests import test_mobile_api
from pear_admin.extensions import db
from pear_admin.orms import SupplierORM, OrderORM, PayORM, PayerORM, MaterialInvoiceORM


class InvoiceLinksTest(unittest.TestCase):
    setUp = test_mobile_api.MobileAPITest.setUp
    tearDown = test_mobile_api.MobileAPITest.tearDown

    def seed(self):
        self.supplier = SupplierORM(type_id=1, name='上海（甲）公司', contact_person='甲', phone='', bank_name='', account_number='')
        other = SupplierORM(type_id=1, name='上海（甲）公司分公司', contact_person='甲', phone='', bank_name='', account_number='')
        payer = PayerORM(type_id=1, name='付款单位')
        db.session.add_all([self.supplier, other, payer]); db.session.flush()
        self.order = OrderORM(order_number='D001', supplier_id=self.supplier.id, supplier_contact_person='甲', material_name='材料', order_amount=1000)
        db.session.add(self.order); db.session.flush()
        self.payments = [PayORM(pay_number=f'P{i}', order_id=self.order.id, payee_supplier_id=s.id, payer_supplier_id=payer.id, current_payment_amount='20.10') for i, s in enumerate([self.supplier, self.supplier, other])]
        self.invoices = [MaterialInvoiceORM(invoice_number=f'I{i}', seller_name=name, total_amount=100, tax_amount=13) for i, name in enumerate([' 上海(甲) 公司 ', '上海（甲）公司', '无关公司', ''])]
        db.session.add_all(self.payments + self.invoices); db.session.commit()
        self.url = f'/api/v1/invoice-links/invoices/{self.invoices[0].id}/payments'

    def link(self, ids):
        return self.client.post(self.url, json={'payment_ids': ids}, headers=self.headers)

    def test_candidates_match_normalized_full_name_not_substring(self):
        self.seed()
        response = self.client.get(self.url, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual({p['id'] for p in response.json['data']['matched']}, {p.id for p in self.payments[:2]})
        self.assertEqual(response.json['data']['linked'], [])

    def test_invoice_add_is_idempotent_preserves_other_invoices_and_visible_in_both_directions(self):
        self.seed()
        self.payments[0].invoices.append(self.invoices[1]); db.session.commit()
        for _ in range(2):
            response = self.link([self.payments[0].id, self.payments[0].id, self.payments[1].id])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['code'], 0)
        self.assertEqual({i.id for i in self.payments[0].invoices}, {self.invoices[0].id, self.invoices[1].id})
        db.session.expire_all()
        data = self.client.get(self.url, headers=self.headers).json['data']
        self.assertEqual(len(data['linked']), 2)
        payment = self.client.get(f'/api/v1/pay/{self.payments[0].id}', headers=self.headers).json['data']
        self.assertIn(self.invoices[0].id, [i['id'] for i in payment['invoices_list']])
        self.assertEqual(payment['current_payment_amount'], '20.10')

    def test_bad_or_mismatching_selection_is_atomic(self):
        self.seed()
        for ids in [[self.payments[0].id, self.payments[2].id], [999], [True], ['1.2'], {}, None]:
            response = self.link(ids)
            self.assertIn(response.status_code, (400, 404))
            self.assertEqual(self.invoices[0].related_pays, [])

    def test_empty_seller_never_matches_and_endpoints_require_login(self):
        self.seed()
        empty = f'/api/v1/invoice-links/invoices/{self.invoices[3].id}/payments'
        self.assertEqual(self.client.get(empty, headers=self.headers).json['data']['matched'], [])
        self.assertIn(self.client.get(self.url).status_code, (401, 403))
        self.assertIn(self.client.post(self.url, json={'payment_ids': [1]}).status_code, (401, 403))

    def test_payment_saves_manual_mismatched_selection_and_shows_reverse_link(self):
        self.seed()
        data = dict(pay_number='NEW', order_id=self.order.id, payee_supplier_id=self.supplier.id,
                    payer_supplier_id=self.payments[0].payer_supplier_id, current_payment_amount='5.00')
        result = self.client.post('/api/v1/pay/', json={**data, 'invoice_ids': [999]}, headers=self.headers).json
        self.assertNotEqual(result['code'], 0)
        self.assertEqual(db.session.query(PayORM).count(), 3)
        result = self.client.post('/api/v1/pay/', json={**data, 'invoice_ids': [self.invoices[2].id]*2}, headers=self.headers).json
        self.assertEqual(result['code'], 0)
        pid = result['data']['id']
        endpoint = f'/api/v1/pay/{pid}'
        result = self.client.put(endpoint, json={'invoice_ids': [self.invoices[0].id, self.invoices[2].id]}, headers=self.headers).json
        self.assertEqual(result['code'], 0)
        db.session.expire_all()
        payment = db.session.get(PayORM, pid)
        self.assertEqual({i.id for i in payment.invoices}, {self.invoices[0].id, self.invoices[2].id})
        result = self.client.put(endpoint, json={'handler': 'should not change', 'invoice_ids': [999]}, headers=self.headers).json
        self.assertNotEqual(result['code'], 0)
        self.assertIsNone(payment.handler)
        for invoice in (self.invoices[0], self.invoices[2]):
            linked = self.client.get(f'/api/v1/invoice-links/invoices/{invoice.id}/payments', headers=self.headers).json['data']['linked']
            self.assertIn(pid, [p['id'] for p in linked])

    def test_payment_preserves_user_choices_when_payee_changes_until_explicitly_removed(self):
        self.seed()
        pay = self.payments[0]
        pay.invoices.append(self.invoices[2]); db.session.commit()
        endpoint = f'/api/v1/pay/{pay.id}'
        result = self.client.put(endpoint, json={'invoice_ids': [self.invoices[2].id], 'handler': '保留原关联'}, headers=self.headers).json
        self.assertEqual(result['code'], 0)
        result = self.client.put(endpoint, json={'payee_supplier_id': self.payments[2].payee_supplier_id}, headers=self.headers).json
        self.assertEqual(result['code'], 0)
        self.assertEqual([i.id for i in pay.invoices], [self.invoices[2].id])
        result = self.client.put(endpoint, json={'invoice_ids': []}, headers=self.headers).json
        self.assertEqual(result['code'], 0)
        self.assertEqual(pay.invoices, [])

    def test_bad_payment_invoice_ids_do_not_clear_existing_links(self):
        self.seed()
        pay = self.payments[0]; pay.invoices.append(self.invoices[0]); db.session.commit()
        for ids in ['bad', {}, [999], [True]]:
            result = self.client.put(f'/api/v1/pay/{pay.id}', json={'invoice_ids': ids}, headers=self.headers).json
            self.assertNotEqual(result['code'], 0)
            self.assertEqual([i.id for i in pay.invoices], [self.invoices[0].id])
