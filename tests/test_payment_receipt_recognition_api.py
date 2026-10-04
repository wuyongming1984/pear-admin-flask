"""Read-only recognition uses receipt authentication and never saves drafts."""
import unittest
from io import BytesIO
import pymupdf
from pear_admin.extensions import db
from pear_admin.orms import PaymentReceiptORM
from tests import test_mobile_api


class ReceiptRecognitionAPITest(unittest.TestCase):
    setUp = test_mobile_api.MobileAPITest.setUp
    tearDown = test_mobile_api.MobileAPITest.tearDown
    base = '/api/v1/payment-receipts'

    def test_recognition_does_not_update_metadata_or_links(self):
        with pymupdf.open() as document:
            page = document.new_page()
            page.insert_text((40, 60), '付款人名称：测试付款有限公司\n收款人名称：测试收款有限公司\n金额：120.50\n付款日期：2026-10-04\n银行流水号：BANK-A', fontname='china-s', fontsize=12)
            content = document.tobytes()
        uploaded = self.client.post(self.base + '/upload', headers=self.headers,
                                   data={'file':(BytesIO(content), '回单.pdf')}).json['data']
        identity = uploaded['id']
        result = self.client.get(f'{self.base}/{identity}/recognize', headers=self.headers)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['code'], 0, result.json)
        self.assertEqual(result.json['data']['fields']['amount'], '120.50')
        self.assertEqual(result.json['data']['fields']['payer_name'], '测试付款有限公司')
        row = db.session.get(PaymentReceiptORM, identity)
        self.assertIsNone(row.amount)
        self.assertEqual(row.payer_name, '')
        self.assertEqual(row.payments, [])
        self.assertIn('no-store', result.headers.get('Cache-Control',''))

    def test_recognition_requires_authentication(self):
        self.assertIn(self.client.get(self.base + '/1/recognize').status_code, (401,403))

    def test_missing_receipt_returns_clear_error(self):
        result = self.client.get(self.base + '/99999/recognize', headers=self.headers)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['code'], -1)
        self.assertIn('回单不存在', result.json['msg'])
