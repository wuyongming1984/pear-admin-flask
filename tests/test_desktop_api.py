import unittest
from tests import test_mobile_api
from pear_admin.extensions import db
from pear_admin.orms import SupplierORM,OrderORM,ProjectORM
from pear_admin.orms.material import MaterialInvoiceORM
from pear_admin.apis.portal import portal_bp

class DesktopAPITest(unittest.TestCase):
    setUp=test_mobile_api.MobileAPITest.setUp
    tearDown=test_mobile_api.MobileAPITest.tearDown

    def test_portal_json_token_scope_and_no_private_credentials(self):
        self.app.register_blueprint(portal_bp)
        anchor=SupplierORM(type_id=1,phone='',bank_name='',account_number='',name='A',contact_person='Contact',access_token='scope-secret')
        other=SupplierORM(type_id=1,phone='',bank_name='',account_number='',name='B',contact_person='Other',access_token='other-secret')
        db.session.add_all([anchor,other]);db.session.flush()
        db.session.add_all([OrderORM(order_number='visible',material_name='m',supplier_id=anchor.id,order_amount=100),OrderORM(order_number='hidden',material_name='m',supplier_id=other.id,order_amount=200)])
        db.session.commit()
        self.assertEqual(self.client.get('/portal/reconcile/no-such-token/data').status_code,404)
        response=self.client.get('/portal/reconcile/scope-secret/data')
        self.assertEqual(response.status_code,200)
        data=response.json['data']
        self.assertEqual(data['analysis']['total_orders'],100)
        self.assertEqual(data['grouped_orders'][0]['orders'][0]['order_number'],'visible')
        self.assertNotIn('hidden',response.text)
        self.assertNotIn('scope-secret',response.text)
        self.assertNotIn('access_token',response.text)

    def test_invoice_project_name_uses_model_field(self):
        project=ProjectORM(project_name='Project attached to invoice')
        db.session.add(project);db.session.flush()
        invoice=MaterialInvoiceORM(invoice_number='desktop-regression',project_id=project.id)
        db.session.add(invoice);db.session.commit()
        response=self.client.get('/api/v1/material/invoice',headers=self.headers)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['data'][0]['project_name'],project.project_name)
