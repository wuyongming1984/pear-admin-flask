"""Editor options must not serialize unrelated documents or attachments."""
import unittest
from decimal import Decimal
from unittest.mock import patch
from sqlalchemy import event
from tests.test_mobile_api import MobileAPITest
from pear_admin.extensions import db
from pear_admin.orms import OrderORM, ProjectORM, PayORM, SupplierORM, PayerORM
from pear_admin.orms.material import MaterialInvoiceORM


class EditorOptionsTest(unittest.TestCase):
    setUp = MobileAPITest.setUp
    tearDown = MobileAPITest.tearDown

    def test_existing_payment_invoice_summary_includes_tax_without_loading_catalog(self):
        invoice = MaterialInvoiceORM(invoice_number='EXISTING', total_amount=100, tax_amount=13)
        payment = PayORM(pay_number='EXISTING-PAYMENT', current_payment_amount=10)
        payment.invoices.append(invoice)
        db.session.add(payment); db.session.commit()
        response = self.client.get(f'/api/v1/pay/{payment.id}', headers=self.headers)
        linked = response.json['data']['invoices_list'][0]
        self.assertEqual(Decimal(linked['total_amount']) + Decimal(linked['tax_amount']), Decimal('113'))

    def test_project_options_skip_attachment_serialization(self):
        db.session.add_all([ProjectORM(project_name=f'项目{i}') for i in range(25)])
        db.session.commit()
        with patch.object(ProjectORM, 'json', side_effect=AssertionError('full project serialization')):
            response = self.client.get('/api/v1/project/?mode=slim&limit=10&page=2', headers=self.headers)
        self.assertEqual(response.json['count'], 25)
        self.assertEqual(len(response.json['data']), 10)
        self.assertEqual(set(response.json['data'][0]), {'id', 'project_name'})

    def test_order_options_keep_payment_preview_fields_with_bounded_queries(self):
        project = ProjectORM(project_name='选项项目')
        supplier = SupplierORM(type_id=1, name='收款公司', contact_person='张工', phone='', bank_name='', account_number='')
        payer = PayerORM(type_id=1, name='付款公司')
        db.session.add_all([project, supplier, payer]); db.session.flush()
        orders = [OrderORM(order_number=f'D{i:03}', project_id=project.id, supplier_id=supplier.id,
                           supplier_contact_person='张工', material_name='stone', material_details='合同材料款',
                           order_amount=Decimal('100.10'), attachments='[]') for i in range(25)]
        db.session.add_all(orders); db.session.flush()
        db.session.add_all([PayORM(pay_number=f'F{i}', order_id=o.id, payer_supplier_id=payer.id,
                                  payee_supplier_id=supplier.id, current_payment_amount=Decimal('10.01'))
                            for i, o in enumerate(orders)])
        db.session.commit(); db.session.remove()
        queries = []
        def track(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith('SELECT'):
                queries.append(statement)
        event.listen(db.engine, 'before_cursor_execute', track)
        try:
            with patch.object(OrderORM, 'json', side_effect=AssertionError('full order serialization')):
                response = self.client.get('/api/v1/order/?mode=options&limit=20', headers=self.headers)
        finally:
            event.remove(db.engine, 'before_cursor_execute', track)
        self.assertEqual(response.json['count'], 25)
        self.assertEqual(len(response.json['data']), 20)
        row = response.json['data'][0]
        self.assertEqual(row['project_name'], '选项项目')
        self.assertEqual(row['material_details'], '合同材料款')
        self.assertEqual(row['supplier_contact_person'], '张工')
        self.assertEqual(Decimal(row['paid_amount']), Decimal('10.01'))
        self.assertEqual(Decimal(row['order_balance']), Decimal('90.09'))
        self.assertNotIn('pays_list', row)
        self.assertNotIn('attachments_list', row)
        self.assertLessEqual(len(queries), 7, queries)
