import unittest
from tests.test_mobile_api import MobileAPITest
from pear_admin.extensions import db
from pear_admin.orms import OrderORM, PayORM, SupplierORM, PayerORM


class PaymentPayeeTest(unittest.TestCase):
    setUp = MobileAPITest.setUp
    tearDown = MobileAPITest.tearDown

    def seed(self):
        suppliers = [SupplierORM(type_id=1, name=name, contact_person='同名负责人',
                                 phone='', bank_name='', account_number=str(i))
                     for i, name in enumerate(['甲公司', '乙公司'])]
        payer = PayerORM(type_id=1, name='付款单位')
        db.session.add_all([*suppliers, payer]); db.session.flush()
        orders = [OrderORM(order_number=f'D{i}', material_name='材料', order_amount=100,
                           supplier_id=s.id, supplier_contact_person=s.contact_person)
                  for i, s in enumerate(suppliers)]
        db.session.add_all(orders); db.session.commit()
        self.suppliers, self.orders = suppliers, orders
        return dict(pay_number='F001', order_id=orders[0].id,
                    payer_supplier_id=payer.id, current_payment_amount='20.10')

    def post(self, data):
        return self.client.post('/api/v1/pay/', json=data, headers=self.headers).json

    def test_create_derives_payee_from_order_even_for_duplicate_contact_names(self):
        data = self.seed()
        result = self.post(data)
        self.assertEqual(result['code'], 0, result)
        pay = db.session.get(PayORM, result['data']['id'])
        self.assertEqual(pay.payee_supplier_id, self.suppliers[0].id)

    def test_create_rejects_another_payee_without_writing(self):
        data = self.seed()
        for value in [self.suppliers[1].id, 999, 'invalid']:
            result = self.post({**data, 'payee_supplier_id': value})
            self.assertNotEqual(result['code'], 0, result)
        self.assertEqual(db.session.scalar(db.select(db.func.count(PayORM.id))), 0)

    def test_invalid_or_unlinked_order_cannot_receive_payment(self):
        data = self.seed()
        self.orders[0].supplier_id = None; db.session.commit()
        for value in [self.orders[0].id, 999, None]:
            self.assertNotEqual(self.post({**data, 'order_id': value})['code'], 0)

    def test_edit_validates_before_mutating_and_rebinds_when_order_changes(self):
        data = self.seed(); result = self.post(data); pid = result['data']['id']
        def update(changes):
            return self.client.put(f'/api/v1/pay/{pid}', json=changes, headers=self.headers).json
        self.assertNotEqual(update({'payee_supplier_id': self.suppliers[1].id,
                                    'current_payment_amount': '99.00'})['code'], 0)
        pay = db.session.get(PayORM, pid)
        self.assertEqual(str(pay.current_payment_amount), '20.10')
        self.assertEqual(pay.payee_supplier_id, self.suppliers[0].id)
        self.assertNotEqual(update({'order_id': self.orders[1].id,
                                    'payee_supplier_id': self.suppliers[0].id})['code'], 0)
        self.assertEqual(update({'order_id': self.orders[1].id})['code'], 0)
        self.assertEqual(pay.payee_supplier_id, self.suppliers[1].id)
        self.assertEqual(update({'handler': '经办人'})['code'], 0)

    def test_existing_mismatch_cannot_be_saved_unchanged(self):
        data = self.seed(); result = self.post(data); pid = result['data']['id']
        pay = db.session.get(PayORM, pid)
        pay.payee_supplier_id = self.suppliers[1].id; db.session.commit()
        result = self.client.put(f'/api/v1/pay/{pid}', json={'handler': '经办人'}, headers=self.headers).json
        self.assertNotEqual(result['code'], 0)
