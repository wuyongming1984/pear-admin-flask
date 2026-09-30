"""Upload preview contracts, with real OSS signing and no network access."""
import time
import unittest
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, unquote, urlparse

import oss2

from tests import test_mobile_api
from pear_admin.extensions import db, oss
from pear_admin.orms import AttachmentORM


class AttachmentUploadPreviewTest(unittest.TestCase):
    setUp = test_mobile_api.MobileAPITest.setUp
    tearDown = test_mobile_api.MobileAPITest.tearDown

    def upload(self, **fields):
        return self.client.post('/api/v1/upload/', headers=self.headers, data={
            'file': (BytesIO(b'preview-image'), '现场照片.jpg'), **fields,
        }).get_json()

    def test_private_oss_upload_has_immediately_usable_signed_url_and_stable_path(self):
        bucket = oss2.Bucket(oss2.Auth('test-key', 'test-secret'),
                             'https://oss-cn-hangzhou.aliyuncs.com', 'test-bucket')
        with patch.object(oss, 'bucket', bucket), patch.object(
                bucket, 'put_object', return_value=SimpleNamespace(status=200)):
            for path in ('order_attachments', 'pay_attachments', 'project_attachments'):
                with self.subTest(path=path):
                    result = self.upload(path=path)
                    self.assertEqual(result['code'], 0, result)
                    data = result['data']
                    parsed = urlparse(data['url'])
                    query = parse_qs(parsed.query)
                    self.assertIn('Signature', query)
                    self.assertGreater(int(query['Expires'][0]), time.time())
                    self.assertTrue(unquote(parsed.path).startswith('/' + path + '/'))
                    self.assertEqual(urlparse(data['file_path']).query, '')
                    self.assertEqual(unquote(urlparse(data['file_path']).path), unquote(parsed.path))

    def test_local_upload_keeps_a_working_relative_url(self):
        result = self.upload(path='order_attachments')
        self.assertEqual(result['code'], 0, result)
        data = result['data']
        self.assertTrue(data['url'].startswith('/uploads/order_attachments/'))
        response = self.client.get(data['url'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b'preview-image')
        response.close()

    def test_project_attachment_stores_durable_path_instead_of_temporary_signature(self):
        project = self.client.post('/api/v1/project/', headers=self.headers,
                                   json={'project_name': 'Preview test'}).get_json()['data']['id']
        bucket = oss2.Bucket(oss2.Auth('test-key', 'test-secret'),
                             'https://oss-cn-hangzhou.aliyuncs.com', 'test-bucket')
        with patch.object(oss, 'bucket', bucket), patch.object(
                bucket, 'put_object', return_value=SimpleNamespace(status=200)):
            result = self.upload(path='project_attachments', project_id=str(project), attachment_code='A1')
            self.assertEqual(result['code'], 0, result)
            data = result['data']
            self.assertIn('Signature=', data['url'])
            stored = db.session.get(AttachmentORM, data['id'])
            self.assertNotIn('Signature=', stored.file_path)
            self.assertEqual(stored.file_path, data['file_path'])
