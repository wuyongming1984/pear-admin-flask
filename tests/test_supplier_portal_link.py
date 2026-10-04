"""Supplier sharing links use an offline disposable DB and preserve legacy scope."""
import unittest
from pathlib import Path

from pear_admin.apis.portal import portal_bp
from pear_admin.extensions import db
from pear_admin.orms import OrderORM, PayORM, ProjectORM, SupplierORM
from tests import test_mobile_api


class SupplierPortalLinkTest(unittest.TestCase):
    def setUp(self):
        test_mobile_api.MobileAPITest.setUp(self)
        self.app.template_folder = str(Path(__file__).resolve().parents[1] / 'templates')
        self.app.register_blueprint(portal_bp)

    tearDown = test_mobile_api.MobileAPITest.tearDown

    def supplier(self, contact='白远', token=None, name='测试供应商'):
        supplier = SupplierORM(type_id=1, name=name, contact_person=contact,
                               phone='', bank_name='', account_number='', access_token=token)
        db.session.add(supplier)
        db.session.commit()
        return supplier

    def generate(self, supplier, payload=None):
        return self.client.post(f'/api/v1/supplier/{supplier.id}/token',
                                headers=self.headers, json=payload)

    def test_reuse_existing_preserves_previously_shared_link(self):
        supplier = self.supplier(token='previously-shared-token')
        for _ in range(2):
            response = self.generate(supplier, {'reuse_existing': True})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['code'], 0)
            self.assertEqual(response.json['data'], {
                'token': 'previously-shared-token',
                'url': '/portal/reconcile/previously-shared-token',
            })
            db.session.expire_all()
            self.assertEqual(db.session.get(SupplierORM, supplier.id).access_token,
                             'previously-shared-token')
            self.assertEqual(self.client.get('/portal/reconcile/previously-shared-token/data').status_code, 200)

    def test_reuse_existing_creates_the_first_link_and_then_keeps_it(self):
        supplier = self.supplier()
        first = self.generate(supplier, {'reuse_existing': True}).json
        self.assertEqual(first['code'], 0)
        token = first['data']['token']
        self.assertRegex(token, r'^[A-Za-z0-9_-]{40,64}$')
        self.assertEqual(first['data']['url'], f'/portal/reconcile/{token}')
        second = self.generate(supplier, {'reuse_existing': True}).json
        self.assertEqual(second['data'], first['data'])
        db.session.expire_all()
        self.assertEqual(db.session.get(SupplierORM, supplier.id).access_token, token)

    def test_default_generation_still_resets_the_supplier_details_link(self):
        supplier = self.supplier()
        for index, payload in enumerate((None, {}, {'reuse_existing': False})):
            with self.subTest(payload=payload):
                old = f'previous-token-{index}'
                supplier.access_token = old
                db.session.commit()
                response = self.generate(supplier, payload)
                self.assertEqual(response.json['code'], 0)
                token = response.json['data']['token']
                self.assertNotEqual(token, old)
                self.assertEqual(self.client.get(f'/portal/reconcile/{old}/data').status_code, 404)
                self.assertEqual(self.client.get(f'/portal/reconcile/{token}/data').status_code, 200)

    def test_generation_requires_authentication_but_valid_shared_links_are_public(self):
        supplier = self.supplier(token='public-supplier-token')
        endpoint = f'/api/v1/supplier/{supplier.id}/token'
        for headers in ({}, {'Authorization': 'Bearer invalid'}):
            with self.subTest(headers=headers):
                response = self.client.post(endpoint, headers=headers, json={'reuse_existing': True})
                self.assertIn(response.status_code, (401, 403, 422))
                db.session.expire_all()
                self.assertEqual(db.session.get(SupplierORM, supplier.id).access_token,
                                 'public-supplier-token')
        public = self.client.get('/portal/reconcile/public-supplier-token/data')
        self.assertEqual(public.status_code, 200)
        self.assertEqual(public.json['data']['supplier']['id'], supplier.id)
        self.assertEqual(self.client.get('/portal/reconcile/unknown-token/data').status_code, 404)
        missing = self.client.post('/api/v1/supplier/99999/token', headers=self.headers,
                                   json={'reuse_existing': True})
        self.assertEqual(missing.json['code'], -1)

    def test_public_reconciliation_keeps_same_contact_orders_and_unlinked_payments_scope(self):
        anchor = self.supplier(' 白远 ', 'shared-contact-token', '供应商甲')
        related = self.supplier('白远', name='供应商乙')
        unrelated = self.supplier('白远远', 'unrelated-token', '其他供应商')
        first_project = ProjectORM(project_name='项目甲')
        second_project = ProjectORM(project_name='项目乙')
        db.session.add_all([first_project, second_project])
        db.session.flush()
        orders = [
            OrderORM(order_number='ANCHOR', material_name='材料', supplier_id=anchor.id,
                     supplier_contact_person='历史标签', project_id=first_project.id, order_amount=100),
            OrderORM(order_number='RELATED', material_name='材料', supplier_id=related.id,
                     supplier_contact_person='白远', project_id=second_project.id, order_amount=200),
            OrderORM(order_number='TEXT-ONLY', material_name='材料', supplier_id=None,
                     supplier_contact_person=' 白远 ', project_id=first_project.id, order_amount=300),
            OrderORM(order_number='UNRELATED', material_name='材料', supplier_id=unrelated.id,
                     supplier_contact_person='白远远', order_amount=900),
        ]
        db.session.add_all(orders)
        db.session.flush()
        db.session.add_all([
            PayORM(pay_number='ANCHOR-PAY', order_id=orders[0].id,
                   payee_supplier_id=anchor.id, current_payment_amount=10),
            PayORM(pay_number='RELATED-PAY', order_id=orders[1].id,
                   payee_supplier_id=related.id, current_payment_amount=20),
            PayORM(pay_number='TEXT-PAY', order_id=orders[2].id, current_payment_amount=30),
            PayORM(pay_number='UNLINKED-ANCHOR', payee_supplier_id=anchor.id, current_payment_amount=5),
            PayORM(pay_number='UNLINKED-RELATED', payee_supplier_id=related.id, current_payment_amount=7),
            PayORM(pay_number='UNLINKED-OTHER', payee_supplier_id=unrelated.id, current_payment_amount=100),
            PayORM(pay_number='OTHER-ORDER-PAY', order_id=orders[3].id,
                   payee_supplier_id=anchor.id, current_payment_amount=99),
        ])
        db.session.commit()
        response = self.client.get('/portal/reconcile/shared-contact-token/data')
        self.assertEqual(response.status_code, 200)
        data = response.json['data']
        self.assertEqual({supplier['id'] for supplier in data['related_suppliers']}, {anchor.id, related.id})
        visible_orders = [order for group in data['grouped_orders'] for order in group['orders']]
        self.assertEqual({order['order_number'] for order in visible_orders}, {'ANCHOR', 'RELATED', 'TEXT-ONLY'})
        self.assertEqual({pay['pay_number'] for order in visible_orders for pay in order['pays']},
                         {'ANCHOR-PAY', 'RELATED-PAY', 'TEXT-PAY'})
        self.assertEqual({pay['pay_number'] for pay in data['unlinked_payments']},
                         {'UNLINKED-ANCHOR', 'UNLINKED-RELATED'})
        self.assertEqual(data['analysis'], {'total_orders': 600.0, 'total_received': 72.0,
                                           'outstanding_balance': 528.0})
        self.assertEqual({group['project_name'] for group in data['grouped_orders']}, {'项目甲', '项目乙'})
        self.assertEqual(set(data['supplier']), {'id', 'name', 'contact_person'})
        other = self.client.get('/portal/reconcile/unrelated-token/data').json['data']
        self.assertEqual({order['order_number'] for group in other['grouped_orders'] for order in group['orders']},
                         {'UNRELATED'})
        self.assertEqual({pay['pay_number'] for pay in other['unlinked_payments']}, {'UNLINKED-OTHER'})
        page = self.client.get('/portal/reconcile/shared-contact-token')
        self.assertEqual(page.status_code, 200)
        self.assertIn('供应商对账单', page.get_data(as_text=True))
        self.assertIn('TEXT-ONLY', page.get_data(as_text=True))
        self.assertNotIn('UNLINKED-OTHER', page.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
