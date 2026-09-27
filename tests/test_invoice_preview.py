"""Render the actual PDF bytes, including private OSS objects served as attachments."""
import base64
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch
import unittest
import pymupdf
from tests import test_mobile_api
from pear_admin.extensions import db, oss
from pear_admin.orms import MaterialInvoiceORM


class InvoicePreviewTest(unittest.TestCase):
    setUp = test_mobile_api.MobileAPITest.setUp
    tearDown = test_mobile_api.MobileAPITest.tearDown

    def seed(self, path='/uploads/original.pdf'):
        with pymupdf.open() as doc:
            for text in ['ORIGINAL FIRST PAGE', 'ORIGINAL SECOND PAGE']:
                page = doc.new_page(width=842, height=595)
                page.insert_text((50, 80), text)
            self.pdf = doc.tobytes()
        Path(self.temp.name, 'original.pdf').write_bytes(self.pdf)
        invoice = MaterialInvoiceORM(invoice_number='PREVIEW-TEST', file_path=path, file_type='pdf')
        db.session.add(invoice)
        db.session.commit()
        return invoice.id

    def get(self, id, page=1, **kwargs):
        return self.client.get(f'/api/v1/material/invoice/{id}/preview-page?page={page}', headers=self.headers, **kwargs)

    def test_local_pdf_pages_are_images_without_download_headers(self):
        id = self.seed()
        first, second = self.get(id), self.get(id, 2)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json['data']['page_count'], 2)
        self.assertEqual(second.json['data']['page'], 2)
        self.assertNotEqual(first.json['data']['image'], second.json['data']['image'])
        self.assertNotIn('Content-Disposition', first.headers)
        self.assertIn('no-store', first.headers['Cache-Control'])
        image = first.json['data']['image']
        self.assertTrue(image.startswith('data:image/png;base64,'))
        pix = pymupdf.Pixmap(base64.b64decode(image.split(',', 1)[1]))
        self.assertLessEqual(max(pix.width, pix.height), 1800)
        self.assertGreater(pix.width, 800)

    def test_private_oss_uses_sdk_and_ignores_attachment_mime(self):
        id = self.seed('https://test-bucket.oss-cn-shanghai.aliyuncs.com/invoices/%E5%8E%9F%E4%BB%B6.pdf')
        bucket = Mock(endpoint='https://oss-cn-shanghai.aliyuncs.com', bucket_name='test-bucket')
        obj = BytesIO(self.pdf)
        obj.headers = {'Content-Type': 'application/octet-stream', 'Content-Disposition': 'attachment'}
        bucket.get_object.return_value = obj
        with patch.object(oss, 'bucket', bucket):
            result = self.get(id)
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.json['data']['image'].startswith('data:image/png;base64,'))
        bucket.get_object.assert_called_once_with('invoices/原件.pdf')

    def test_requires_login_and_handles_missing_file(self):
        id = self.seed()
        self.assertIn(self.client.get(f'/api/v1/material/invoice/{id}/preview-page').status_code, (401, 403))
        self.assertEqual(self.get(999999).status_code, 404)
        Path(self.temp.name, 'original.pdf').unlink()
        self.assertEqual(self.get(id).status_code, 404)

    def test_rejects_bad_pages_and_corrupt_pdf(self):
        id = self.seed()
        for page in [0, -1, 'bad', 3]:
            self.assertEqual(self.get(id, page).status_code, 400)
        Path(self.temp.name, 'original.pdf').write_bytes(b'<Error>AccessDenied</Error>')
        self.assertEqual(self.get(id).status_code, 422)

    def test_rejects_path_escape_and_arbitrary_remote_url(self):
        id = self.seed('/uploads/../outside.pdf')
        self.assertEqual(self.get(id).status_code, 400)
        inv = db.session.get(MaterialInvoiceORM, id)
        inv.file_path = 'http://127.0.0.1/private.pdf'
        db.session.commit()
        self.assertEqual(self.get(id).status_code, 400)

    def test_oversized_file_is_rejected_before_render(self):
        id = self.seed()
        with patch('pear_admin.invoice_preview.MAX_FILE_BYTES', 8):
            self.assertEqual(self.get(id).status_code, 413)


if __name__ == '__main__':
    unittest.main()
