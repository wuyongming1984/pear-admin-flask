"""Offline API regressions: isolated in-memory DB, no application factory/scheduler."""
import json
import base64
from io import BytesIO
from datetime import timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from flask import Flask
from flask_jwt_extended import create_access_token
from pear_admin.apis import register_apis
from pear_admin.extensions import db, jwt, oss
from sqlalchemy import text
from pear_admin.orms import AttachmentORM, ProjectORM, UserORM, RoleORM, SupplierORM, PayerORM, PayORM
from pear_admin.orms.material import MaterialInvoiceORM
from pear_admin.views.index import index_bp


class MobileAPITest(unittest.TestCase):
    def setUp(self):
        self.network = patch('socket.socket.connect', side_effect=AssertionError('Network prohibited'))
        self.network.start()
        self.local_storage = patch.object(oss, 'bucket', None)
        self.local_storage.start()
        self.temp = tempfile.TemporaryDirectory()
        self.app = Flask(__name__, static_folder=self.temp.name)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite://',
                               JWT_SECRET_KEY='offline-test-secret-at-least-32-characters', JWT_VERIFY_SUB=False,
                               UPLOAD_FOLDER=self.temp.name)
        db.init_app(self.app)
        jwt.init_app(self.app)
        register_apis(self.app)
        self.app.register_blueprint(index_bp)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        user = UserORM(username='admin', nickname='Admin', password='test', mobile='', email='', department_id=None)
        user.role_list.append(RoleORM(name='Admin', code='admin'))
        db.session.add(user)
        db.session.commit()
        self.headers = {'Authorization': 'Bearer ' + create_access_token(identity=user)}
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        self.temp.cleanup()
        self.network.stop()
        self.local_storage.stop()

    def post(self, path, payload):
        return self.client.post('/api/v1/' + path + '/', json=payload, headers=self.headers).get_json()

    def put(self, path, payload):
        return self.client.put('/api/v1/' + path, json=payload, headers=self.headers).get_json()

    def project(self, name='Project', **extra):
        result = self.post('project', dict(project_name=name, **extra))
        self.assertEqual(result['code'], 0, result)
        return result['data']['id']

    def attachment(self, pid):
        att = AttachmentORM(project_id=pid, attachment_code='A', filename='a.pdf',
                            original_filename='a.pdf', file_path='/uploads/a.pdf', file_size=12)
        db.session.add(att)
        db.session.commit()
        return att.id

    def test_project_detail_and_unauthorized(self):
        pid = self.project()
        for path in [f'project/{pid}', 'project/', 'order/', 'pay/']:
            self.assertIn(self.client.get('/api/v1/' + path).status_code, (401, 403))
        response = self.client.get(f'/api/v1/project/{pid}', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['data']['id'], pid)
        self.assertEqual(self.client.get('/api/v1/project/99999', headers=self.headers).json['code'], -1)

    def test_real_expired_token_returns_legacy_403_envelope(self):
        user = db.session.scalar(db.select(UserORM).where(UserORM.username == 'admin'))
        token = create_access_token(identity=user, expires_delta=timedelta(seconds=-5))
        response = self.client.get('/api/v1/project/', headers={'Authorization': 'Bearer ' + token})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json, {'code': -1, 'msg': 'token 已过期，请重新登录'})

    def test_project_attachment_omission_preserves_and_explicit_list_replaces(self):
        pid = self.project()
        aid = self.attachment(pid)
        self.assertEqual(self.put(f'project/{pid}', {'project_name': 'Edited'})['code'], 0)
        self.assertEqual(db.session.get(AttachmentORM, aid).project_id, pid)
        self.assertEqual(self.put(f'project/{pid}', {'attachments': json.dumps([{'id': str(aid), 'code': 'B'}])})['code'], 0)
        self.assertEqual(db.session.get(AttachmentORM, aid).attachment_code, 'B')
        self.assertEqual(self.put(f'project/{pid}', {'attachments': []})['code'], 0)
        self.assertIsNone(db.session.get(AttachmentORM, aid))

    def test_invalid_attachments_rollback_create_and_edit(self):
        pid = self.project()
        aid = self.attachment(pid)
        foreign = self.attachment(self.project('Other'))
        for invalid in ['not-json', {}, None, [42], [{'id': 99999}], [{'id': foreign, 'code': 'X'}], [{'code': 'X'}]]:
            with self.subTest(invalid=invalid):
                count = db.session.query(ProjectORM).count()
                result = self.post('project', {'project_name': 'Bad', 'attachments': invalid})
                self.assertEqual(result['code'], -1, result)
                self.assertEqual(db.session.query(ProjectORM).count(), count)
                result = self.put(f'project/{pid}', {'project_name': 'Bad', 'attachments': invalid})
                self.assertEqual(result['code'], -1, result)
                self.assertEqual(db.session.get(ProjectORM, pid).project_name, 'Project')
                self.assertIsNotNone(db.session.get(AttachmentORM, aid))

    def test_project_attachment_insert_failure_rolls_back(self):
        with patch.object(db.session, 'commit', side_effect=RuntimeError('simulated commit failure')):
            result = self.post('project', {'project_name': 'Bad', 'attachments': [{'code': 'X', 'filename': 'x.pdf', 'url': '/uploads/x.pdf'}]})
        self.assertEqual(result['code'], -1)
        self.assertEqual(db.session.query(ProjectORM).count(), 0)
        self.assertEqual(db.session.query(AttachmentORM).count(), 0)

    def test_project_create_attachment_formats(self):
        for attachments in [[{'code': 'X', 'filename': 'x.pdf', 'name': '原件.pdf', 'url': '/uploads/x.pdf', 'size': 10}],
                            json.dumps([{'code': 'Y', 'url': '/uploads/y.pdf', 'name': 'y.pdf'}])]:
            pid = self.project(attachments=attachments)
            self.assertEqual(db.session.query(AttachmentORM).filter_by(project_id=pid).count(), 1)

    def test_pay_detail_preserves_raw_attachment_paths(self):
        raw = json.dumps([{'name': 'invoice.pdf', 'url': '/uploads/invoice.pdf'}])
        pay = PayORM(pay_number='RAW', attachments=raw)
        db.session.add(pay)
        db.session.commit()
        result = self.client.get(f'/api/v1/pay/{pay.id}', headers=self.headers).json
        self.assertEqual(result['data']['attachments'], raw)

    def test_order_exact_project_filter_and_payment_invoice_preservation(self):
        p1, p2 = self.project('Same'), self.project('Same suffix')
        supplier = SupplierORM(type_id=1, name='Supplier', contact_person='Contact', phone='1', bank_name='B', account_number='1')
        payer = PayerORM(type_id=1, name='Payer')
        invoice = MaterialInvoiceORM(invoice_number='INV', seller_name='Supplier')
        db.session.add_all([supplier, payer, invoice])
        db.session.commit()
        orders = []
        for pid in [p1, p2]:
            result = self.post('order', {'material_name': 'Steel', 'order_amount': '100.00', 'project_id': pid, 'supplier_id': supplier.id})
            self.assertEqual(result['code'], 0, result)
            orders.append(result['data']['id'])
        response = self.client.get(f'/api/v1/order/?project_id={p1}', headers=self.headers).json
        self.assertEqual([item['id'] for item in response['data']], [orders[0]])
        self.assertEqual(self.client.get('/api/v1/order/?project_name=Same', headers=self.headers).json['count'], 2)
        self.assertEqual(self.put(f'order/{orders[0]}', {'material_name': 'Edited'})['code'], 0)
        result = self.post('pay', {'pay_number': 'PAY-1', 'order_id': orders[0], 'payer_supplier_id': payer.id,
                                  'payee_supplier_id': supplier.id, 'current_payment_amount': '20.50', 'invoice_ids': [invoice.id]})
        self.assertEqual(result['code'], 0, result)
        payid = result['data']['id']
        self.assertEqual(self.put(f'pay/{payid}', {'handler': 'Edited'})['code'], 0)
        self.assertEqual([i.id for i in db.session.get(PayORM, payid).invoices], [invoice.id])
        self.assertEqual(self.client.get(f'/api/v1/pay/{payid}', headers=self.headers).json['data']['handler'], 'Edited')

    def test_mobile_quick_search_matches_partial_business_fields(self):
        project_id = self.project('东区道路绿化项目', project_full_name='东区道路绿化工程')
        self.project('西区苗圃')
        supplier = SupplierORM(type_id=1, name='青禾苗木供应商', contact_person='张经理',
                               phone='13812345678', bank_name='建设银行', account_number='123')
        payer = PayerORM(type_id=1, name='市政建设付款单位')
        db.session.add_all([supplier, payer])
        db.session.commit()
        order = self.post('order', {'material_name': '香樟苗木', 'order_amount': '100.00',
                                    'project_id': project_id, 'supplier_id': supplier.id,
                                    'supplier_contact_person': '张经理'})
        self.assertEqual(order['code'], 0, order)
        payment = self.post('pay', {'pay_number': 'FK-SEARCH-1', 'order_id': order['data']['id'],
                                    'payer_supplier_id': payer.id, 'payee_supplier_id': supplier.id,
                                    'current_payment_amount': '20.00'})
        self.assertEqual(payment['code'], 0, payment)
        cases = [('project/', '道路绿化', project_id),
                 ('order/', '香樟', order['data']['id']),
                 ('order/', '东区道路', order['data']['id']),
                 ('order/', '张经', order['data']['id']),
                 ('pay/', '建设付款', payment['data']['id']),
                 ('pay/', '东区道路', payment['data']['id']),
                 ('supplier/', '青禾', supplier.id),
                 ('supplier/', '张经', supplier.id),
                 ('payer/', '市政建设', payer.id)]
        for endpoint, term, expected_id in cases:
            with self.subTest(endpoint=endpoint, term=term):
                response = self.client.get('/api/v1/' + endpoint, query_string={'q': term},
                                           headers=self.headers)
                self.assertEqual(response.status_code, 200)
                self.assertEqual([item['id'] for item in response.json['data']], [expected_id])
        by_contact = self.client.get('/api/v1/order/', query_string={'supplier_contact_person': '张经'},
                                     headers=self.headers).json
        self.assertEqual([item['id'] for item in by_contact['data']], [order['data']['id']])

    def test_mobile_entry_and_nested_upload(self):
        mobile = Path(self.temp.name) / 'mobile'
        mobile.mkdir()
        (mobile / 'index.html').write_text('<html>Mobile shell</html>', encoding='utf-8')
        response = self.client.get('/m/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-cache', response.headers['Cache-Control'])
        response.close()
        (Path(self.temp.name) / 'nested').mkdir()
        (Path(self.temp.name) / 'nested' / 'a.txt').write_text('attachment', encoding='utf-8')
        response = self.client.get('/uploads/nested/a.txt')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b'attachment')
        response.close()
        self.assertEqual(self.client.get('/uploads/../outside.txt').status_code, 404)

    def schema_snapshot(self):
        return tuple(db.session.execute(text(
            "SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name"
        )).all())

    def upload_and_read(self, kind, filename, content):
        response = self.client.post('/api/v1/upload/', headers=self.headers,
                                    data={'file': (BytesIO(content), filename),
                                          'path': f'{kind}_attachments', 'attachment_code': 'mobile'},
                                    content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertEqual(result['code'], 0, result)
        attachment = result['data']
        self.assertEqual(attachment['original_filename'], filename)
        self.assertEqual(attachment['size'], len(content))
        self.assertTrue(attachment['url'].startswith(f'/uploads/{kind}_attachments/'))
        stored_path = Path(self.temp.name) / f'{kind}_attachments' / attachment['filename']
        self.assertTrue(stored_path.resolve().is_relative_to(Path(self.temp.name).resolve()))
        self.assertEqual(stored_path.read_bytes(), content)
        download = self.client.get(attachment['url'])
        try:
            self.assertEqual(download.status_code, 200)
            self.assertEqual(download.data, content)
        finally:
            download.close()
        return attachment

    def test_chinese_uploads_complete_business_flow_and_schema_unchanged(self):
        schema_before = self.schema_snapshot()
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aMuoAAAAASUVORK5CYII=')
        pdf = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n'
        uploads = {}
        for kind in ('project', 'order', 'pay'):
            uploads[kind] = [self.upload_and_read(kind, '施工现场-photo.png', png),
                             self.upload_and_read(kind, '采购合同-contract.pdf', pdf)]
        supplier = SupplierORM(type_id=1, name='测试供应商', contact_person='张工', phone='13800000000',
                               bank_name='测试银行', account_number='TEST-001')
        payer = PayerORM(type_id=1, name='测试付款单位')
        invoice = MaterialInvoiceORM(invoice_number='TEST-INVOICE', total_amount=30, seller_name='测试供应商')
        db.session.add_all([supplier, payer, invoice])
        db.session.commit()
        pid = self.project('中文集成项目', project_status='1', project_amount='1000.50',
                           start_date='2026-09-01', attachments=json.dumps(uploads['project'], ensure_ascii=False))
        result = self.post('order', {'project_id': pid, 'supplier_id': supplier.id, 'material_name': '钢材',
                                     'supplier_contact_person': '张工', 'order_amount': '200.50',
                                     'attachments': json.dumps(uploads['order'], ensure_ascii=False)})
        self.assertEqual(result['code'], 0, result)
        oid = result['data']['id']
        result = self.post('pay', {'pay_number': 'INTEGRATION-PAY', 'order_id': oid,
                                  'payer_supplier_id': payer.id, 'payee_supplier_id': supplier.id,
                                  'current_payment_amount': '30.25', 'invoice_amount': '30.00',
                                  'invoice_ids': [invoice.id],
                                  'attachments': json.dumps(uploads['pay'], ensure_ascii=False)})
        self.assertEqual(result['code'], 0, result)
        payid = result['data']['id']
        original = {}
        for kind, rid in [('project', pid), ('order', oid), ('pay', payid)]:
            original[kind] = self.client.get(f'/api/v1/{kind}/{rid}', headers=self.headers).json['data']
        for path, payload in [(f'project/{pid}', {'project_full_name': '项目编辑成功', 'end_date': '2026-12-31'}),
                              (f'order/{oid}', {'material_details': '订单编辑成功', 'order_amount': '201.50'}),
                              (f'pay/{payid}', {'handler': '李工', 'current_payment_amount': '31.25', 'invoice_amount': None})]:
            result = self.put(path, payload)
            self.assertEqual(result['code'], 0, result)
        edited = {}
        for kind, rid in [('project', pid), ('order', oid), ('pay', payid)]:
            edited[kind] = self.client.get(f'/api/v1/{kind}/{rid}', headers=self.headers).json['data']
            self.assertEqual(edited[kind]['attachments'], original[kind]['attachments'])
            self.assertEqual(len(edited[kind]['attachments_list']), 2)
        self.assertEqual(edited['project']['project_full_name'], '项目编辑成功')
        self.assertEqual(edited['order']['project_id'], pid)
        self.assertEqual(edited['order']['material_details'], '订单编辑成功')
        self.assertEqual(edited['order']['order_amount'], '201.50')
        self.assertEqual(edited['pay']['order_id'], oid)
        self.assertEqual(edited['pay']['current_payment_amount'], '31.25')
        self.assertEqual([item['id'] for item in edited['pay']['invoices_list']], [invoice.id])
        self.assertEqual(edited['order']['pays_count'], 1)
        self.assertEqual(edited['order']['pays_list'][0]['id'], payid)
        self.assertEqual(self.client.get(f'/api/v1/order/?project_id={pid}', headers=self.headers).json['count'], 1)
        self.assertEqual(self.client.get(f'/api/v1/pay/?order_id={oid}', headers=self.headers).json['count'], 1)
        # Re-submit the original project attachment IDs while appending one upload.
        extra = self.upload_and_read('project', '补充合同-extra.pdf', pdf + b'\n% extra')
        preserved_ids = [item['id'] for item in original['project']['attachments_list']]
        result = self.put(f'project/{pid}', {'attachments': original['project']['attachments_list'] + [extra]})
        self.assertEqual(result['code'], 0, result)
        current = self.client.get(f'/api/v1/project/{pid}', headers=self.headers).json['data']['attachments_list']
        self.assertEqual(len(current), 3)
        self.assertTrue(set(preserved_ids).issubset({item['id'] for item in current}))
        self.assertEqual(self.schema_snapshot(), schema_before)

    def test_chinese_project_uploads_same_second_are_unique_and_keep_extension(self):
        from datetime import datetime
        for extension in ('jpg', 'pdf'):
            with self.subTest(extension=extension):
                uploads = []
                with patch('pear_admin.apis.upload.datetime') as clock:
                    clock.now.return_value = datetime(2026, 9, 24, 12, 0, 0)
                    for filename, content in [(f'现场照片.{extension}', b'first-file'),
                                              (f'施工照片.{extension}', b'second-file')]:
                        uploads.append(self.upload_and_read('project', filename, content))
                self.assertTrue(uploads[0]['filename'].endswith('.' + extension))
                self.assertTrue(uploads[1]['filename'].endswith('.' + extension))
                self.assertNotEqual(uploads[0]['url'], uploads[1]['url'])
                for attachment, expected in zip(uploads, (b'first-file', b'second-file')):
                    response = self.client.get(attachment['url'])
                    try:
                        self.assertEqual(response.data, expected)
                    finally:
                        response.close()


if __name__ == '__main__':
    unittest.main()
