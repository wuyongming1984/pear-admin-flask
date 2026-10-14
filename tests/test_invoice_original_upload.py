"""Original uploads use disposable storage/SQLite and offline OCR responses."""
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

import pymupdf

from pear_admin.extensions import db, oss
from pear_admin.orms import MaterialInvoiceORM, MaterialInvoiceDetailORM
from tests import test_invoice_links, test_mobile_api


class InvoiceOriginalUploadTest(unittest.TestCase):
    setUp = test_mobile_api.MobileAPITest.setUp
    tearDown = test_mobile_api.MobileAPITest.tearDown

    def seed(self, **values):
        invoice = MaterialInvoiceORM(invoice_number='26000000000000000001',
                                     total_amount=Decimal('100.00'), tax_amount=Decimal('13.00'),
                                     buyer_tax_num='BUYER', seller_tax_num='SELLER',
                                     seller_name='原销售方', remarks='原备注', project_id=42,
                                     ocr_status='imported', ocr_result='{"tax_excel":{"source_row":2}}')
        for key, value in values.items():
            setattr(invoice, key, value)
        invoice.details.append(MaterialInvoiceDetailORM(name='原明细', amount=Decimal('100.00')))
        db.session.add(invoice)
        db.session.commit()
        return invoice

    def pdf(self):
        with pymupdf.open() as document:
            document.new_page().insert_text((50, 80), 'ORIGINAL INVOICE')
            return document.tobytes()

    def upload(self, invoice, ocr=None, **fields):
        recognized = {'invoice_number': invoice.invoice_number, 'invoice_code': invoice.invoice_code,
                      'buyer_tax_num': 'BUYER', 'seller_tax_num': 'SELLER',
                      'total_amount': '999.00', 'total_tax': '99.00', 'seller_name': 'OCR销售方',
                      'details': [{'name': 'OCR明细', 'amount': '999.00'}]}
        if ocr:
            recognized.update(ocr)
        with patch('pear_admin.ocr_utils.get_ocr_instance') as engine:
            engine.return_value.recognize_invoice.return_value = recognized
            return self.client.post('/api/v1/material/invoice/upload', headers=self.headers, data={
                'files': (BytesIO(self.pdf()), '原件.pdf'), 'project_id': '999', **fields,
            }).json

    def assert_preserved(self, invoice):
        db.session.expire_all()
        self.assertEqual(invoice.total_amount, Decimal('100.00'))
        self.assertEqual(invoice.tax_amount, Decimal('13.00'))
        self.assertEqual(invoice.seller_name, '原销售方')
        self.assertEqual(invoice.remarks, '原备注')
        self.assertEqual(invoice.project_id, 42)
        self.assertEqual(invoice.ocr_status, 'imported')
        self.assertEqual(invoice.ocr_result, '{"tax_excel":{"source_row":2}}')
        self.assertEqual([row.name for row in invoice.details], ['原明细'])

    def test_existing_missing_original_is_attached_and_pdf_preview_works(self):
        invoice = self.seed()
        result = self.upload(invoice)
        self.assertEqual(result['data']['failed'], 0, result)
        self.assertEqual(result['data']['attached'], 1)
        self.assertEqual(result['data']['uploaded'], 0)
        self.assertEqual(result['data']['invoices'][0]['id'], invoice.id)
        self.assertTrue(result['data']['invoices'][0]['attached'])
        self.assertEqual(db.session.query(MaterialInvoiceORM).count(), 1)
        self.assert_preserved(invoice)
        self.assertEqual(invoice.file_name, '原件.pdf')
        self.assertEqual(invoice.file_type, 'pdf')
        preview = self.client.get(f'/api/v1/material/invoice/{invoice.id}/preview-page?page=1', headers=self.headers)
        self.assertEqual(preview.status_code, 200, preview.json)
        self.assertTrue(preview.json['data']['image'].startswith('data:image/png;base64,'))
        legacy_preview = self.client.get(f'/api/v1/material/invoice/preview/{invoice.id}', headers=self.headers)
        self.assertEqual(legacy_preview.status_code, 200)
        with pymupdf.open(stream=legacy_preview.data, filetype='pdf') as document:
            self.assertIn('ORIGINAL INVOICE', document[0].get_text())

    def test_non_imported_record_with_empty_original_can_be_completed(self):
        invoice = self.seed(ocr_status='success', ocr_result='{}', file_path='')
        result = self.upload(invoice)
        self.assertEqual(result['data']['failed'], 0, result)
        self.assertEqual(result['data']['attached'], 1)
        self.assertEqual(invoice.ocr_result, '{}')

    def test_attaching_an_original_preserves_unknown_amounts_in_the_response(self):
        invoice = self.seed()
        db.session.execute(db.update(MaterialInvoiceORM).where(MaterialInvoiceORM.id == invoice.id)
                           .values(total_amount=None, tax_amount=None))
        db.session.commit()
        result = self.upload(invoice, reuse_existing='1')
        self.assertEqual(result['data']['failed'], 0, result)
        attached = result['data']['invoices'][0]
        self.assertIsNone(attached['total_amount'])
        self.assertIsNone(attached['tax_amount'])
        self.assertIsNone(invoice.total_amount)
        self.assertIsNone(invoice.tax_amount)

    def test_repeat_upload_preserves_first_original(self):
        invoice = self.seed()
        self.assertEqual(self.upload(invoice)['data']['failed'], 0)
        original = invoice.file_path
        result = self.upload(invoice)
        self.assertEqual(result['data']['failed'], 1)
        self.assertEqual(invoice.file_path, original)
        self.assertEqual(db.session.query(MaterialInvoiceORM).count(), 1)

    def test_payment_upload_attaches_original_without_saving_new_payment_links(self):
        test_invoice_links.InvoiceLinksTest.seed(self)
        invoice = self.seed()
        self.payments[1].invoices.append(invoice)
        db.session.commit()
        result = self.upload(invoice, reuse_existing='1')
        self.assertEqual(result['data']['failed'], 0, result)
        self.assertEqual(result['data']['attached'], 1)
        self.assertEqual(result['data']['invoices'][0]['seller_name'], '原销售方')
        self.assertEqual(self.payments[0].invoices, [])
        self.assertEqual([row.id for row in self.payments[1].invoices], [invoice.id])

    def test_traditional_same_number_different_codes_do_not_attach_to_wrong_record(self):
        invoice = self.seed(invoice_number='12345678', invoice_code='111111111111')
        result = self.upload(invoice, {'invoice_code': '222222222222'})
        self.assertEqual(result['data']['uploaded'], 1, result)
        self.assertIsNone(invoice.file_path)
        self.assertNotEqual(result['data']['invoices'][0]['id'], invoice.id)

    def test_ambiguous_existing_number_requires_review(self):
        invoice = self.seed()
        self.seed()
        result = self.upload(invoice)
        self.assertEqual(result['data']['failed'], 1, result)
        self.assertTrue(all(not row.file_path for row in MaterialInvoiceORM.query.all()))

    def test_missing_traditional_code_does_not_guess_original(self):
        invoice = self.seed(invoice_number='12345678', invoice_code='111111111111')
        result = self.upload(invoice, {'invoice_code': None})
        self.assertEqual(result['data']['failed'], 1, result)
        self.assertIsNone(invoice.file_path)

    def test_conflicting_tax_number_rejects_attachment(self):
        invoice = self.seed()
        result = self.upload(invoice, {'seller_tax_num': 'OTHER'})
        self.assertEqual(result['data']['failed'], 1, result)
        self.assertIsNone(invoice.file_path)
        self.assert_preserved(invoice)

    def test_failed_oss_upload_leaves_existing_record_unchanged(self):
        invoice = self.seed()
        with patch.object(oss, 'bucket', Mock()), patch.object(oss, 'upload_file', side_effect=RuntimeError('offline failure')):
            result = self.upload(invoice)
        self.assertEqual(result['data']['failed'], 1)
        self.assertIn('offline failure', result['data']['errors'][0]['reason'])
        self.assertIsNone(invoice.file_path)
        self.assert_preserved(invoice)

    def test_private_oss_original_is_attached_and_previews_through_sdk(self):
        invoice = self.seed()
        bucket = Mock(endpoint='https://oss-cn-shanghai.aliyuncs.com', bucket_name='test-bucket')
        bucket.sign_url.return_value = 'https://test-bucket.oss-cn-shanghai.aliyuncs.com/invoices/original.pdf?Signature=test'
        bucket.get_object.return_value = BytesIO(self.pdf())
        with patch.object(oss, 'bucket', bucket), patch.object(oss, 'upload_file', return_value='https://test-bucket.oss-cn-shanghai.aliyuncs.com/invoices/original.pdf'):
            result = self.upload(invoice)
            self.assertEqual(result['data']['attached'], 1, result)
            self.assertIn('Signature=', result['data']['invoices'][0]['url'])
            self.assertNotIn('Signature=', invoice.file_path)
            preview = self.client.get(f'/api/v1/material/invoice/{invoice.id}/preview-page?page=1', headers=self.headers)
        self.assertEqual(preview.status_code, 200, preview.json)
        self.assert_preserved(invoice)

    def test_an_original_added_during_storage_is_not_overwritten(self):
        invoice = self.seed()
        def concurrent_upload(*args, **kwargs):
            invoice.file_path = '/uploads/concurrent.pdf'
            db.session.commit()
            return 'https://test-bucket.oss-cn-shanghai.aliyuncs.com/invoices/second.pdf'
        with patch.object(oss, 'bucket', Mock()), patch.object(oss, 'upload_file', side_effect=concurrent_upload):
            result = self.upload(invoice)
        self.assertEqual(result['data']['failed'], 1, result)
        self.assertEqual(invoice.file_path, '/uploads/concurrent.pdf')

    def retry(self, pending, target):
        with patch('pear_admin.ocr_utils.get_ocr_instance') as engine:
            engine.return_value.recognize_invoice.return_value = {
                'invoice_number': target.invoice_number, 'buyer_tax_num': 'BUYER', 'seller_tax_num': 'SELLER'}
            return self.client.post('/api/v1/material/invoice/ocr', headers=self.headers,
                                    json={'invoice_ids': [pending.id]}).json

    def pending(self):
        path = Path(self.temp.name, 'pending.pdf')
        path.write_bytes(self.pdf())
        pending = MaterialInvoiceORM(invoice_number='TEMP-retry', file_path='/uploads/pending.pdf',
                                     file_name='pending.pdf', file_type='pdf', ocr_status='failed')
        db.session.add(pending)
        db.session.commit()
        return pending

    def test_ocr_retry_transfers_original_and_preserves_payment_links(self):
        test_invoice_links.InvoiceLinksTest.seed(self)
        target, pending = self.seed(), self.pending()
        pending_id, path = pending.id, pending.file_path
        self.payments[0].invoices.append(pending)
        self.payments[1].invoices.append(target)
        db.session.commit()
        result = self.retry(pending, target)
        self.assertEqual(result['data']['success'], 1, result)
        self.assertEqual(result['data']['results'][0]['invoice_id'], target.id)
        self.assertTrue(Path(self.temp.name, 'pending.pdf').is_file())
        self.assertEqual(target.file_path, path)
        self.assertIsNone(db.session.get(MaterialInvoiceORM, pending_id))
        self.assertEqual([row.id for row in self.payments[0].invoices], [target.id])
        self.assertEqual([row.id for row in self.payments[1].invoices], [target.id])
        self.assert_preserved(target)

    def test_ocr_retry_does_not_delete_pending_file_when_target_already_has_original(self):
        target, pending = self.seed(file_path='/uploads/first.pdf'), self.pending()
        pending_id, path = pending.id, pending.file_path
        result = self.retry(pending, target)
        self.assertEqual(result['data']['failed'], 1)
        self.assertTrue(Path(self.temp.name, 'pending.pdf').is_file())
        self.assertIsNotNone(db.session.get(MaterialInvoiceORM, pending_id))
        self.assertEqual(target.file_path, '/uploads/first.pdf')
