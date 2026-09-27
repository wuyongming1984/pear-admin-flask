"""PC material/nursery regressions using SQLite memory only, with networking disabled."""
import unittest
from pathlib import Path
from unittest.mock import patch
from flask import Flask
from pear_admin.extensions import db
from pear_admin.apis.material import material_api
from pear_admin.apis.nursery import nursery_api
from pear_admin.views.material import material_bp
from pear_admin.views.nursery import nursery_bp
from pear_admin.orms.material import MaterialPlanningORM, MaterialInboundORM, MaterialInventoryORM, MaterialOutboundORM
from pear_admin.orms.nursery import NurseryPlantORM, NurseryTransactionORM


class MaterialNurseryPCTest(unittest.TestCase):
    def setUp(self):
        self.network = patch('socket.socket.connect', side_effect=AssertionError('Network prohibited'))
        self.network.start()
        self.app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / 'templates'))
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite://')
        db.init_app(self.app)
        self.app.register_blueprint(material_api, url_prefix='/material')
        self.app.register_blueprint(nursery_api, url_prefix='/api/nursery')
        self.app.register_blueprint(material_bp)
        self.app.register_blueprint(nursery_bp)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        self.network.stop()

    def post(self, path, data):
        return self.client.post(path, json=data).get_json()

    def test_empty_api_pages(self):
        for path in ['/material/' + p for p in ['options', 'planning', 'inbound', 'inventory', 'outbound', 'invoice', 'invoice/list', 'dashboard/stats']] + ['/api/nursery/' + p for p in ['inventory', 'transactions', 'orders', 'dashboard/stats']]:
            with self.subTest(path=path):
                r = self.client.get(path)
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.json['code'], 0, r.json)

    def test_page_rendering_empty_database(self):
        paths = ['/view/material/' + p for p in ['dashboard', 'planning', 'inbound', 'inventory', 'outbound', 'outbound_records', 'invoice', 'planning/add', 'inbound/add', 'outbound/add', 'outbound/batch_add', 'invoice/add']]
        paths += ['/nursery/' + p for p in ['dashboard', 'inventory', 'transactions', 'inbound', 'outbound', 'orders', 'logs', 'settings']]
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_generated_inbound_reserves_planning_once_and_confirmation_is_idempotent(self):
        row = MaterialPlanningORM(material_name='Steel', material_spec='S', material_unit='kg', planned_total_quantity=10, planned_remaining_quantity=10, planned_price=2)
        db.session.add(row); db.session.commit()
        self.assertEqual(self.post('/material/planning/generate_inbound', {'items': [{'id': row.id, 'quantity': 3}]})['code'], 0)
        inbound = MaterialInboundORM.query.one()
        for _ in range(2):
            self.assertEqual(self.post('/material/inbound/batch_confirm', {'ids': [inbound.id]})['code'], 0)
        self.assertEqual(float(row.planned_remaining_quantity), 7)
        self.assertEqual(float(MaterialInventoryORM.query.one().current_stock), 3)

    def test_manual_inbound_reservation_and_delete_are_balanced(self):
        plan = MaterialPlanningORM(material_name='Steel', material_spec='S', material_unit='kg', planned_total_quantity=10, planned_remaining_quantity=10)
        db.session.add(plan); db.session.commit()
        result = self.post('/material/inbound', {'material_name':'Steel', 'material_spec':'S', 'material_unit':'kg', 'inbound_quantity':3, 'inbound_price':2})
        self.assertEqual(result['code'], 0)
        self.assertEqual(float(plan.planned_remaining_quantity), 7)
        inbound = MaterialInboundORM.query.one()
        self.assertEqual(float(inbound.inbound_total_amount), 6)
        self.assertEqual(self.client.delete('/material/inbound/' + str(inbound.id)).json['code'], 0)
        self.assertEqual(float(plan.planned_remaining_quantity), 10)

    def test_direct_outbound_reports_completed_quantity(self):
        inv = MaterialInventoryORM(material_name='Steel', current_stock=10, seller_quantity=3, seller_price=4, total_value=20)
        db.session.add(inv); db.session.commit()
        self.assertEqual(self.post('/material/outbound/batch', {'items':[{'inventory_id': inv.id}], 'direct_confirm':True})['code'], 0)
        row = self.client.get('/material/outbound?status=completed').json['data'][0]
        self.assertEqual(float(row['completed_sales_quantity']), 3)
        self.assertEqual(float(row['seller_quantity']), 0)
        self.assertEqual(float(inv.current_stock), 7)
        self.assertEqual(float(inv.total_value), 14)

    def test_invoice_accepts_browser_date_and_invalid_date_does_not_poison_session(self):
        self.assertEqual(self.post('/material/invoice', {'invoice_number':'BAD', 'invoice_date':'2026-02-30'})['code'], 1)
        good = self.post('/material/invoice', {'invoice_number':'GOOD', 'invoice_date':'2026-09-24', 'total_amount':'12.50'})
        self.assertEqual(good['code'], 0, good)
        result = self.client.get('/material/invoice').json
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['data'][0]['invoice_date'], '2026-09-24')

    def test_nursery_order_edit_non_inventory_quantity_and_date(self):
        result = self.post('/api/nursery/outbound', {'date':'2026-09-01', 'items':[{'name':'Delivery', 'is_non_inventory':True, 'quantity':2, 'price':3}]})
        self.assertTrue(result['success'])
        tx = NurseryTransactionORM.query.one()
        self.assertEqual(tx.create_at.strftime('%Y-%m-%d'), '2026-09-01')
        result = self.client.put('/api/nursery/order/' + tx.order_no, json={'date':'2026-09-02', 'items':[{'id':tx.id, 'quantity':4, 'price':5}]}).json
        self.assertTrue(result['success'], result)
        self.assertEqual(float(tx.quantity), 4)
        self.assertEqual(float(tx.total_price), 20)
        self.assertEqual(tx.create_at.strftime('%Y-%m-%d'), '2026-09-02')

    def test_nursery_invalid_numbers_are_rejected_without_writes(self):
        for value in ['bad', 'NaN', 'Infinity', -1, 0]:
            with self.subTest(value=value):
                r = self.post('/api/nursery/inbound', {'name':'Tree', 'quantity':value, 'price':1})
                self.assertFalse(r['success'])
                r = self.post('/api/nursery/outbound', {'items':[{'name':'Other', 'quantity':value, 'price':1, 'is_non_inventory':True}]})
                self.assertFalse(r['success'])
        self.assertEqual(NurseryPlantORM.query.count(), 0)
        self.assertEqual(NurseryTransactionORM.query.count(), 0)

    def test_failed_nursery_batch_rolls_back_earlier_item(self):
        p = NurseryPlantORM(name='Tree', quantity=10, price=2)
        db.session.add(p); db.session.commit()
        r = self.post('/api/nursery/outbound', {'items':[{'plant_id':p.id, 'quantity':2, 'price':3}, {'plant_id':p.id, 'quantity':99, 'price':3}]})
        self.assertFalse(r['success'])
        db.session.commit()  # A caller's later commit must not persist rejected partial work.
        self.assertEqual(float(db.session.get(NurseryPlantORM, p.id).quantity), 10)
        self.assertEqual(NurseryTransactionORM.query.count(), 0)

    def test_nursery_same_second_orders_are_distinct(self):
        import datetime
        fixed = datetime.datetime(2026, 9, 24, 10, 0)
        from types import SimpleNamespace
        class FrozenDateTime(datetime.datetime):
            @classmethod
            def now(cls):
                return fixed
        with patch('pear_admin.apis.nursery.datetime', SimpleNamespace(datetime=FrozenDateTime)):
            numbers = [self.post('/api/nursery/outbound', {'items':[{'name':'Other', 'quantity':1, 'price':2, 'is_non_inventory':True}]})['order_no'] for _ in range(2)]
        self.assertNotEqual(*numbers)

    def test_nursery_grid_requests_all_stock_and_filters(self):
        db.session.add_all([NurseryPlantORM(name='Tree ' + str(i), quantity=1, price=2) for i in range(15)])
        db.session.commit()
        self.assertEqual(len(self.client.get('/api/nursery/inventory?all=1').json['data']), 15)
        self.assertEqual(self.client.get('/api/nursery/inventory?all=1&name=Tree%2014').json['count'], 1)

    def test_log_snapshot_edit_delete_matches_ui_without_changing_stock(self):
        p = NurseryPlantORM(name='Tree', quantity=10, price=2)
        db.session.add(p); db.session.flush()
        tx = NurseryTransactionORM(order_no='IN-X', type='in', plant_id=p.id, plant_name='Tree', quantity=10, price=2, total_price=20)
        db.session.add(tx); db.session.commit()
        result = self.client.put('/api/nursery/transaction/' + str(tx.id), json={'quantity':5, 'price':3, 'remark':'Corrected'} )
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.json['success'])
        self.assertEqual(float(tx.total_price), 15)
        self.assertEqual(float(p.quantity), 10)
        result = self.client.delete('/api/nursery/transaction/' + str(tx.id))
        self.assertTrue(result.json['success'])
        self.assertEqual(float(p.quantity), 10)
        self.assertEqual(NurseryTransactionORM.query.count(), 0)

    def test_inbound_edit_moves_reservation_to_new_material_and_recalculates_amount(self):
        plans = [MaterialPlanningORM(material_name=name, material_spec='S', planned_total_quantity=10, planned_remaining_quantity=10) for name in ['Steel', 'Wood']]
        db.session.add_all(plans); db.session.commit()
        self.post('/material/inbound', {'material_name':'Steel', 'material_spec':'S', 'inbound_quantity':3, 'inbound_price':2})
        row = MaterialInboundORM.query.one()
        result = self.client.put('/material/inbound/' + str(row.id), json={'id':str(row.id), 'material_name':'Wood', 'inbound_quantity':4, 'inbound_price':3}).json
        self.assertEqual(result['code'], 0)
        self.assertEqual(float(plans[0].planned_remaining_quantity), 10)
        self.assertEqual(float(plans[1].planned_remaining_quantity), 6)
        self.assertEqual(float(row.inbound_total_amount), 12)

    def test_all_templates_render_and_inline_javascript_parses(self):
        import re
        import subprocess
        from flask import render_template
        inv = MaterialInventoryORM(material_name="Quote ' ", material_spec='S', current_stock=10, seller_quantity=3)
        inbound = MaterialInboundORM(material_name='Steel', inbound_quantity=2, inbound_price=3)
        db.session.add_all([inv, inbound]); db.session.commit()
        root = Path(self.app.template_folder)
        for folder in ['material', 'nursery']:
            for file in (root / folder).rglob('*.html'):
                with self.subTest(file=str(file)):
                    html = render_template(file.relative_to(root).as_posix(), projects=[], suppliers=[], inventory_items=[inv], target_inventory=inv, inbound=inbound)
                    scripts = []
                    for attrs, content in re.findall(r'<script([^>]*)>(.*?)</script>', html, flags=re.S | re.I):
                        if 'src=' not in attrs and ('type=' not in attrs or 'javascript' in attrs):
                            scripts.append(content)
                    result = subprocess.run(['node', '-e', 'new Function(require("fs").readFileSync(0,"utf8"))'], input='\n'.join(scripts), text=True, encoding='utf-8', capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_material_rejects_invalid_quantities_without_stock_mutation(self):
        plan = MaterialPlanningORM(material_name='Steel', planned_remaining_quantity=10, planned_total_quantity=10)
        inv = MaterialInventoryORM(material_name='Steel', current_stock=10, seller_quantity=10)
        db.session.add_all([plan, inv]); db.session.commit()
        for qty in [-1, 0, 'NaN', 'Infinity']:
            with self.subTest(qty=qty):
                result = self.post('/material/planning/generate_inbound', {'items':[{'id':plan.id, 'quantity':qty}]})
                self.assertEqual(result['code'], 1)
                result = self.post('/material/outbound', {'material_name':'Steel', 'outbound_quantity':qty})
                self.assertEqual(result['code'], 1)
        self.assertEqual(float(inv.current_stock), 10)
        self.assertEqual(float(inv.seller_quantity), 10)
        self.assertEqual(float(plan.planned_remaining_quantity), 10)
        self.assertEqual(MaterialInboundORM.query.count(), 0)
        self.assertEqual(MaterialOutboundORM.query.count(), 0)

    def test_outbound_form_uses_selected_inventory_id(self):
        inv = MaterialInventoryORM(material_name='Steel', material_spec='S', current_stock=10, seller_quantity=10)
        db.session.add(inv); db.session.commit()
        result = self.post('/material/outbound', {'material_inventory_id':inv.id, 'outbound_quantity':2})
        self.assertEqual(result['code'], 0, result)
        self.assertEqual(MaterialOutboundORM.query.one().inventory_id, inv.id)

    def test_missing_edit_record_is_404(self):
        self.assertEqual(self.client.get('/view/material/inbound/edit/999').status_code, 404)


if __name__ == '__main__':
    unittest.main()
