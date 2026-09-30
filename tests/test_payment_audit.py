from datetime import datetime
import unittest

from flask_jwt_extended import create_access_token
from pear_admin.extensions import db
from pear_admin.orms import PayORM, UserORM
from tests.test_payment_payee import PaymentPayeeTest


class PaymentAuditTest(unittest.TestCase):
    setUp = PaymentPayeeTest.setUp
    tearDown = PaymentPayeeTest.tearDown
    seed = PaymentPayeeTest.seed
    post = PaymentPayeeTest.post

    def create(self, **changes):
        result = self.post({**self.seed(), **changes})
        self.assertEqual(result['code'], 0, result)
        return result['data']['id']

    def detail(self, pid):
        return self.client.get(f'/api/v1/pay/{pid}', headers=self.headers).json['data']

    def test_defaults_handler_and_records_authenticated_creator_and_server_time(self):
        start = datetime.now().replace(microsecond=0)
        pid = self.create(create_at='2023-08-04 00:00:00', generated_at='2000-01-01 00:00:00',
                          created_by_id=999, created_by_username='forged', created_by_nickname='冒用')
        data = self.detail(pid)
        self.assertEqual(data['handler'], 'Admin')
        self.assertEqual(data['created_by_username'], 'admin')
        self.assertEqual(data['created_by_nickname'], 'Admin')
        self.assertNotEqual(data['created_by_id'], 999)
        self.assertGreaterEqual(datetime.fromisoformat(data['generated_at']), start)
        self.assertEqual(data['create_at'], '2023-08-04 00:00:00')

    def test_manual_handler_and_immutable_creation_survive_another_users_edit(self):
        pid = self.create(handler='手动经办人')
        original = self.detail(pid)
        self.assertEqual(original['handler'], '手动经办人')
        self.assertIn('generated_at', original)
        creator = db.session.scalar(db.select(UserORM).where(UserORM.username == 'admin'))
        creator.nickname = '后来修改的昵称'
        editor = UserORM(username='editor', nickname='编辑人员', password='test', mobile='', email='', department_id=None)
        db.session.add(editor); db.session.commit()
        headers = {'Authorization': 'Bearer ' + create_access_token(identity=editor)}
        changes = dict(handler='修改后经办人', generated_at='2001-01-01 00:00:00',
                       created_by_id=editor.id, created_by_username='forged', created_by_nickname='伪造',
                       updated_at='2001-01-01 00:00:00', updated_by_id=999, updated_by_username='forged', updated_by_nickname='伪造')
        result = self.client.put(f'/api/v1/pay/{pid}', json=changes, headers=headers).json
        self.assertEqual(result['code'], 0, result)
        data = self.detail(pid)
        for key in ['generated_at', 'created_by_id', 'created_by_username', 'created_by_nickname']:
            self.assertEqual(data[key], original[key])
        self.assertEqual(data['handler'], '修改后经办人')
        self.assertEqual(data['updated_by_id'], editor.id)
        self.assertEqual(data['updated_by_username'], 'editor')
        self.assertEqual(data['updated_by_nickname'], '编辑人员')
        self.assertGreaterEqual(data['updated_at'], data['generated_at'])

    def test_edit_historical_payment_does_not_invent_creator(self):
        data = self.seed()
        pay = PayORM(**data, handler='原经办人', payee_supplier_id=self.suppliers[0].id)
        db.session.add(pay); db.session.commit()
        result = self.client.put(f'/api/v1/pay/{pay.id}', json={'handler': '新经办人'}, headers=self.headers).json
        self.assertEqual(result['code'], 0, result)
        result = self.detail(pay.id)
        self.assertIn('generated_at', result)
        self.assertIsNone(result['generated_at'])
        self.assertIsNone(result['created_by_id'])
        self.assertEqual(result['updated_by_username'], 'admin')
