"""Offline cold-session query budgets for lists, with distinct related records."""
import unittest
from sqlalchemy import event
from tests import test_mobile_api
from pear_admin.extensions import db
from pear_admin.apis.portal import portal_bp
from pear_admin.orms import ProjectORM, SupplierORM, PayerORM, OrderORM, PayORM, AttachmentORM
from pear_admin.orms.material import (
    MaterialPlanningORM, MaterialInboundORM, MaterialInventoryORM,
    MaterialOutboundORM, MaterialInvoiceORM,
)
from pear_admin.orms.nursery import NurseryTransactionORM


class SystemQueryEfficiencyTest(unittest.TestCase):
    tearDown = test_mobile_api.MobileAPITest.tearDown

    def setUp(self):
        test_mobile_api.MobileAPITest.setUp(self)
        self.app.register_blueprint(portal_bp)

    def counted(self, path):
        db.session.remove()
        statements = []
        def capture(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)
        event.listen(db.engine, 'before_cursor_execute', capture)
        try:
            response = self.client.get(path, headers=self.headers)
        finally:
            event.remove(db.engine, 'before_cursor_execute', capture)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['code'], 0, response.json)
        print(f'QUERY_AUDIT {path}: SQL={len(statements)}', flush=True)
        return response.json, len(statements)

    def seed(self, size=20):
        for i in range(size):
            project = ProjectORM(project_name=f'Project {i}')
            supplier = SupplierORM(type_id=1, name=f'Supplier {i}', contact_person=f'Contact {i}',
                                   phone='', bank_name='', account_number='')
            seller = SupplierORM(type_id=1, name=f'Seller {i}', contact_person=f'Seller contact {i}',
                                 phone='', bank_name='', account_number='')
            payer = PayerORM(type_id=1, name=f'Payer {i}')
            db.session.add_all([project, supplier, seller, payer]); db.session.flush()
            invoice = MaterialInvoiceORM(invoice_number=f'INV-{i}', total_amount=10, tax_amount=1,
                                         project_id=project.id, supplier_id=supplier.id)
            order = OrderORM(order_number=f'D-{i}', project_id=project.id, supplier_id=supplier.id,
                             material_name='Steel', order_amount=100)
            # Separate order suppliers expose lazy loading even when payment payees are eager.
            empty_order = OrderORM(order_number=f'EMPTY-{i}', project_id=project.id, supplier_id=seller.id,
                                   material_name='Empty', order_amount=100)
            db.session.add_all([invoice, order, empty_order]); db.session.flush()
            pay = PayORM(pay_number=f'F-{i}', order_id=order.id, payer_supplier_id=payer.id,
                         payee_supplier_id=supplier.id, current_payment_amount=2)
            pay.invoices.append(invoice)
            inventory = MaterialInventoryORM(project_id=project.id, supplier_id=supplier.id,
                seller_id=seller.id, latest_invoice_id=invoice.id, material_name='Steel',
                current_stock=8, seller_quantity=2, seller_price=3, total_value=16)
            db.session.add_all([pay, inventory]); db.session.flush()
            db.session.add_all([
                AttachmentORM(project_id=project.id, attachment_code='A', filename='a.pdf',
                    original_filename='a.pdf', file_path='/uploads/a.pdf', file_size=12),
                MaterialPlanningORM(project_id=project.id, supplier_id=supplier.id,
                    material_name='Steel', material_spec=None, planned_price=2,
                    planned_total_quantity=10, planned_remaining_quantity=8),
                MaterialInboundORM(project_id=project.id, supplier_id=supplier.id, invoice_id=invoice.id,
                    material_name='Steel', material_spec=None, inbound_quantity=2, status='pending'),
                MaterialInboundORM(project_id=project.id, material_name='Steel', material_spec=None,
                    inbound_quantity=99, status='completed'),
                MaterialOutboundORM(inventory_id=inventory.id, invoice_id=invoice.id, status='pending'),
                NurseryTransactionORM(order_no=f'N-{i}', type='out', plant_name='Tree', quantity=2,
                    price=3, total_price=6),
                NurseryTransactionORM(order_no=f'N-{i}', type='out', plant_name='Delivery', quantity=1,
                    price=4, total_price=4),
                NurseryTransactionORM(order_no=f'N-{i}', type='in', plant_name='Excluded', quantity=10,
                    price=10, total_price=100),
            ])
        db.session.commit()

    def test_list_budgets_and_payloads(self):
        self.seed()
        cases = [
            ('project/?limit=100', 4, 20, 'project_name', 'Project 0'),
            ('order/?limit=100', 7, 40, 'supplier_name', 'Seller 0'),
            ('pay/?limit=100', 4, 20, 'payer_supplier_name', 'Payer 0'),
            ('material/planning?limit=100', 3, 20, 'pending_inbound_quantity', '2.00'),
            ('material/inbound?limit=100&status=pending', 2, 20, 'invoice_number', 'INV-0'),
            ('material/inventory?limit=100', 2, 20, 'seller_name', 'Seller 0'),
            ('material/outbound?limit=100', 2, 20, 'seller_name', 'Seller 0'),
        ]
        for path, budget, count, key, value in cases:
            with self.subTest(path=path):
                result, queries = self.counted('/api/v1/' + path)
                self.assertEqual(result['count'], count)
                self.assertEqual(len(result['data']), count)
                self.assertIn(value, [row[key] for row in result['data']])
                if 'planning?' in path:
                    self.assertTrue(all(row['planned_total_amount'] == '20.00' for row in result['data']))
                if path.startswith('pay/'):
                    self.assertTrue(all(len(row['invoices_list']) == 1 for row in result['data']))
                self.assertLessEqual(queries, budget)

    def test_project_counters_are_batched_and_status_scoped(self):
        self.seed()
        db.session.add(ProjectORM(project_name='Empty project'))
        db.session.add(MaterialOutboundORM(status='pending'))  # Orphan must not count for any project.
        db.session.commit()
        result, queries = self.counted('/api/v1/material/options')
        for row in result['data']['projects']:
            expected = 0 if row['name'] == 'Empty project' else 1
            self.assertEqual([row[key] for key in ('planning_count', 'inbound_count', 'inventory_count',
                                                  'outbound_count', 'invoice_count')], [expected] * 5)
        self.assertLessEqual(queries, 7)

    def test_planning_null_keys_duplicates_and_pagination(self):
        for spec, remaining in ((None, 1), (None, 0), ('', -1)):
            db.session.add(MaterialPlanningORM(material_name='Steel', material_spec=spec,
                                               planned_remaining_quantity=remaining))
        for spec, qty, status in ((None, 2, 'pending'), (None, 3, 'pending'), ('', 7, 'pending'),
                                  (None, 99, 'completed')):
            db.session.add(MaterialInboundORM(material_name='Steel', material_spec=spec,
                                              inbound_quantity=qty, status=status))
        db.session.commit()
        result, queries = self.counted('/api/v1/material/planning?limit=100')
        self.assertEqual([r['pending_inbound_quantity'] for r in result['data']], ['5.00', '5.00', '7.00'])
        self.assertLessEqual(queries, 3)
        filtered, _ = self.counted('/api/v1/material/planning?remaining_status=%3C0&limit=1')
        self.assertEqual(filtered['count'], 1)
        self.assertEqual(filtered['data'][0]['pending_inbound_quantity'], '7.00')
        empty, _ = self.counted('/api/v1/material/planning?page=99&limit=1')
        self.assertEqual(empty['data'], [])

    def test_nursery_orders_fetch_details_in_batch(self):
        self.seed()
        result, queries = self.counted('/api/v1/nursery/orders')
        self.assertEqual(len(result['data']), 20)
        for order in result['data']:
            self.assertEqual(order['total'], 10)
            self.assertEqual(order['item_count'], 2)
            self.assertEqual(len(order['items']), 2)
            self.assertTrue(all(item['order_no'] == order['order_no'] for item in order['items']))
        self.assertLessEqual(queries, 2)

    def test_larger_pages_keep_query_counts_bounded(self):
        self.seed(100)
        for path, budget in (
            ('project/?limit=100', 4), ('order/?limit=100', 7), ('pay/?limit=100', 4),
            ('material/planning?limit=100', 3), ('material/inbound?limit=100', 2),
            ('material/inventory?limit=100', 2), ('material/outbound?limit=100', 2),
            ('material/options', 7), ('nursery/orders', 2),
        ):
            with self.subTest(path=path):
                _, queries = self.counted('/api/v1/' + path)
                self.assertLessEqual(queries, budget)

    def test_optional_relations_snapshots_and_project_filter(self):
        self.seed(2)
        project_id = ProjectORM.query.filter_by(project_name='Project 0').one().id
        inventory = MaterialInventoryORM.query.filter_by(project_id=project_id).one()
        own_seller = SupplierORM.query.filter_by(name='Supplier 1').one()
        db.session.add_all([
            MaterialInventoryORM(material_name='No relations'),
            MaterialInboundORM(material_name='No relations'),
            MaterialOutboundORM(status='pending'),
            MaterialOutboundORM(inventory_id=inventory.id, status='completed', material_name='Snapshot',
                project_id=project_id, seller_id=own_seller.id, seller_quantity=0, seller_price=0),
        ])
        db.session.commit()
        for resource, expected in (('inbound', 2), ('inventory', 1), ('outbound', 1), ('planning', 1)):
            result, _ = self.counted(f'/api/v1/material/{resource}?project_id={project_id}&limit=1')
            self.assertEqual(result['count'], expected)
            self.assertEqual(len(result['data']), 1)
        result, queries = self.counted('/api/v1/material/outbound?status=completed')
        row = result['data'][0]
        self.assertEqual(row['material_name'], 'Snapshot')
        self.assertEqual(row['seller_name'], 'Supplier 1')
        self.assertEqual(row['inbound_invoice_number'], 'INV-0')
        self.assertEqual(float(row['seller_quantity']), 0)
        self.assertEqual(float(row['seller_price']), 0)
        self.assertLessEqual(queries, 2)
        pending, _ = self.counted('/api/v1/material/outbound')
        self.assertEqual(pending['count'], 2)  # The orphan is still excluded.
        for resource in ('inbound', 'inventory'):
            result, _ = self.counted(f'/api/v1/material/{resource}?limit=100')
            row = next(r for r in result['data'] if r['material_name'] == 'No relations')
            self.assertEqual(row['project_name'], '')
            self.assertEqual(row['supplier_name'], '')

    def test_unlinked_portal_payments_preserve_token_scope(self):
        supplier = SupplierORM(type_id=1, name='Portal supplier', contact_person='Portal contact',
                               access_token='offline-query-token', phone='', bank_name='', account_number='')
        outsider = SupplierORM(type_id=1, name='Other', contact_person='Other contact',
                               phone='', bank_name='', account_number='')
        db.session.add_all([supplier, outsider]); db.session.flush()
        for i in range(20):
            payer = PayerORM(type_id=1, name=f'Payer {i}')
            db.session.add(payer); db.session.flush()
            db.session.add(PayORM(pay_number=f'P-{i}', payer_supplier_id=payer.id,
                                  payee_supplier_id=supplier.id, current_payment_amount=2))
        db.session.add(PayORM(pay_number='PRIVATE', payee_supplier_id=outsider.id, current_payment_amount=999))
        db.session.commit()
        result, queries = self.counted('/portal/reconcile/offline-query-token/data')
        self.assertNotIn('PRIVATE', str(result))
        self.assertIn('Payer 19', str(result))
        self.assertLessEqual(queries, 4)
        self.assertEqual(self.client.get('/portal/reconcile/invalid/data').status_code, 404)
