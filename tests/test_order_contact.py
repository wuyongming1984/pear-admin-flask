import unittest
from tests.test_mobile_api import MobileAPITest
from pear_admin.extensions import db
from pear_admin.orms import OrderORM, ProjectORM, SupplierORM


class OrderContactTest(unittest.TestCase):
    setUp = MobileAPITest.setUp
    tearDown = MobileAPITest.tearDown

    def seed(self):
        project = ProjectORM(project_name='联系人测试项目')
        supplier = SupplierORM(type_id=1, name='甲公司', contact_person='张工',
                               phone='13800000001', bank_name='', account_number='')
        db.session.add_all([project, supplier]); db.session.commit()
        return dict(project_id=project.id, supplier_id=supplier.id, material_name='材料',
                    order_amount='123.45', supplier_contact_person='张工')

    def post(self, data):
        return self.client.post('/api/v1/order/', json=data, headers=self.headers).json

    def test_contact_must_exist_and_match_supplier(self):
        data = self.seed()
        for changes in ({'supplier_contact_person': ''}, {'supplier_contact_person': '不存在'},
                        {'supplier_id': 999}, {'supplier_id': None, 'supplier_contact_person': '不存在'}):
            with self.subTest(changes=changes):
                self.assertNotEqual(self.post({**data, **changes})['code'], 0)
        self.assertEqual(db.session.scalar(db.select(db.func.count(OrderORM.id))), 0)

    def test_phone_and_default_nickname_come_from_authoritative_records(self):
        data = self.seed()
        result = self.post({**data, 'contact_phone': '伪造电话'})
        self.assertEqual(result['code'], 0, result)
        order = db.session.get(OrderORM, result['data']['id'])
        self.assertEqual(order.contact_phone, '13800000001')
        self.assertEqual(order.material_manager, 'Admin')
        self.assertNotEqual(order.material_manager, 'admin')
        result = self.post({**data, 'material_manager': '指定负责人'})
        self.assertEqual(db.session.get(OrderORM, result['data']['id']).material_manager, '指定负责人')

    def test_duplicate_names_require_supplier_identity(self):
        data = self.seed()
        other = SupplierORM(type_id=1, name='乙公司', contact_person='张工',
                            phone='13800000002', bank_name='', account_number='')
        db.session.add(other); db.session.commit()
        self.assertNotEqual(self.post({**data, 'supplier_id': None})['code'], 0)
        result = self.post({**data, 'supplier_id': other.id})
        self.assertEqual(result['code'], 0, result)
        self.assertEqual(db.session.get(OrderORM, result['data']['id']).contact_phone, other.phone)

    def test_edit_rejects_unregistered_contact_and_updates_phone(self):
        data = self.seed(); result = self.post(data); oid = result['data']['id']
        response = self.client.put(f'/api/v1/order/{oid}', headers=self.headers,
                                   json={'supplier_contact_person': '不在名录中'}).json
        self.assertNotEqual(response['code'], 0)
        response = self.client.put(f'/api/v1/order/{oid}', headers=self.headers,
                                   json={'contact_phone': '自由填写'}).json
        self.assertEqual(response['code'], 0, response)
        self.assertEqual(db.session.get(OrderORM, oid).contact_phone, '13800000001')
