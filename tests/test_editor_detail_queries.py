"""Cold-session SQL budgets and payload preservation for document editors."""
import json
import unittest
from decimal import Decimal
from sqlalchemy import event
from tests import test_mobile_api
from pear_admin.extensions import db
from pear_admin.orms import OrderORM, PayORM, PayerORM, ProjectORM, SupplierORM, MaterialInvoiceORM


class EditorDetailQueriesTest(unittest.TestCase):
    setUp = test_mobile_api.MobileAPITest.setUp
    tearDown = test_mobile_api.MobileAPITest.tearDown

    def seed(self, size):
        project = ProjectORM(project_name='查询计数项目')
        db.session.add(project); db.session.flush()
        suppliers = [SupplierORM(type_id=1, name=f'收款单位{i}', contact_person='联系人',
                                phone='', bank_name='', account_number='') for i in range(size)]
        payers = [PayerORM(type_id=1, name=f'付款单位{i}') for i in range(size)]
        db.session.add_all(suppliers + payers); db.session.flush()
        order = OrderORM(order_number='D-QUERY', project_id=project.id, supplier_id=suppliers[0].id,
                         supplier_contact_person='联系人', material_name='石材', order_amount=Decimal('1000.00'),
                         attachments=json.dumps([{'name': '订单.pdf', 'url': '/uploads/order.pdf'}]))
        db.session.add(order); db.session.flush()
        payments = [PayORM(pay_number=f'F{i}', order_id=order.id, payer_supplier_id=payers[i].id,
                           payee_supplier_id=suppliers[i].id, current_payment_amount=Decimal('1.25'),
                           attachments=json.dumps([{'name': '付款.pdf', 'url': '/uploads/payment.pdf'}]))
                    for i in range(size)]
        invoice = MaterialInvoiceORM(invoice_number='INV-QUERY', total_amount=100, tax_amount=13)
        payments[0].invoices.append(invoice)
        db.session.add_all(payments); db.session.commit()
        return order.id, payments[0].id

    def get_counted(self, path):
        # Seeding and prior requests must not populate the identity map.
        db.session.remove()
        statements = []
        def capture(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)
        event.listen(db.engine, 'before_cursor_execute', capture)
        try:
            result = self.client.get('/api/v1' + path, headers=self.headers)
        finally:
            event.remove(db.engine, 'before_cursor_execute', capture)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['code'], 0)
        return result.json['data'], statements

    def test_order_detail_queries_are_bounded_with_distinct_payment_parties(self):
        oid, _ = self.seed(100)
        data, queries = self.get_counted(f'/order/{oid}')
        self.assertEqual(len(data['pays_list']), 100)
        self.assertEqual({p['payer_supplier_name'] for p in data['pays_list']}, {f'付款单位{i}' for i in range(100)})
        self.assertEqual({p['payee_supplier_name'] for p in data['pays_list']}, {f'收款单位{i}' for i in range(100)})
        self.assertEqual(data['supplier_name'], '收款单位0')
        self.assertEqual(data['project_name'], '查询计数项目')
        self.assertEqual(Decimal(data['paid_amount']), Decimal('125'))
        self.assertEqual(Decimal(data['order_balance']), Decimal('875'))
        self.assertEqual(data['attachments_list'][0]['url'], '/uploads/order.pdf')
        self.assertLessEqual(len(queries), 3, f'{len(queries)} SQL statements')

    def test_payment_detail_joins_scalar_relations_and_keeps_invoices(self):
        _, pid = self.seed(1)
        data, queries = self.get_counted(f'/pay/{pid}')
        self.assertEqual(data['order_number'], 'D-QUERY')
        self.assertEqual(data['project_name'], '查询计数项目')
        self.assertEqual(data['payer_supplier_name'], '付款单位0')
        self.assertEqual(data['payee_supplier_name'], '收款单位0')
        self.assertEqual(data['invoices_list'][0]['invoice_number'], 'INV-QUERY')
        self.assertEqual(Decimal(data['invoices_list'][0]['tax_amount']), Decimal('13'))
        self.assertEqual(data['attachments_list'][0]['url'], '/uploads/payment.pdf')
        self.assertLessEqual(len(queries), 3, f'{len(queries)} SQL statements')

    def test_optional_relations_and_missing_records_keep_existing_behavior(self):
        order = OrderORM(order_number='NO-PROJECT', material_name='材料', order_amount=10)
        payment = PayORM(pay_number='NO-ORDER', current_payment_amount=10)
        db.session.add_all([order, payment]); db.session.commit()
        oid, pid = order.id, payment.id
        data, _ = self.get_counted(f'/order/{oid}')
        self.assertIsNone(data['project_name'])
        self.assertIsNone(data['supplier_name'])
        self.assertEqual(data['pays_list'], [])
        data, _ = self.get_counted(f'/pay/{pid}')
        self.assertIsNone(data['order_number'])
        self.assertIsNone(data['payer_supplier_name'])
        self.assertEqual(data['invoices_list'], [])
        for path in ('/order/99999', '/pay/99999'):
            self.assertEqual(self.client.get('/api/v1' + path, headers=self.headers).json['code'], -1)
            self.assertIn(self.client.get('/api/v1' + path).status_code, (401, 403))
