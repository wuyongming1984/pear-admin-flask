"""Read-only receipt recognition: real local PDFs and mocked OCR HTTP only."""
import importlib
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from flask import Flask
import pymupdf
import requests
from werkzeug.exceptions import BadRequest


class ReceiptRecognitionTest(unittest.TestCase):
    def setUp(self):
        try:
            self.module = importlib.import_module('pear_admin.receipt_recognition')
        except ModuleNotFoundError:
            self.fail('Receipt recognition has not been implemented')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = Flask(__name__)
        self.app.config.update(UPLOAD_FOLDER=self.temp.name)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.addCleanup(self.ctx.pop)
        self.env = patch.dict(os.environ, {'BAIDU_OCR_API_KEY': '', 'BAIDU_OCR_SECRET_KEY': ''})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.network = patch('socket.socket.connect', side_effect=AssertionError('Network prohibited'))
        self.network.start()
        self.addCleanup(self.network.stop)

    def pdf(self, pages, filename='receipt.pdf'):
        with pymupdf.open() as doc:
            for lines in pages:
                page = doc.new_page(width=900, height=900)
                for index, line in enumerate(lines):
                    if isinstance(line, tuple):
                        x, y, text = line
                    else:
                        x, y, text = 40, 40 + index * 24, line
                    page.insert_text((x, y), text, fontname='china-s', fontsize=12)
            data = doc.tobytes()
        Path(self.temp.name, filename).write_bytes(data)
        return '/uploads/' + filename, data

    def png(self):
        pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 100, 100), False)
        pix.clear_with(255)
        data = pix.tobytes('png')
        Path(self.temp.name, 'receipt.png').write_bytes(data)
        return '/uploads/receipt.png', data

    def recognize(self, path, file_type='pdf'):
        return self.module.recognize_receipt(path, file_type)

    def ocr_http(self, words, token=None):
        token = token or {'access_token': 'test-token'}
        response = {'words_result_num': len(words), 'words_result': words, 'log_id': 1234}
        return patch.object(self.module.requests, 'post', side_effect=[
            Mock(status_code=200, json=Mock(return_value=token)),
            Mock(status_code=200, json=Mock(return_value=response)),
        ])

    @staticmethod
    def word(value, average=0.99, minimum=0.95):
        return {'word': value, 'probability': {'average': average, 'min': minimum}}

    def test_chinese_labelled_pdf_and_source_are_read_only(self):
        path, original = self.pdf([[
            '中国工商银行网上银行电子回单',
            '付款人户名：上海甲园林有限公司', '收款人户名：苏州乙苗木有限公司',
            '小写金额：￥1,234.50元', '交易日期：2026年10月4日',
            '回单编号：BANK-20261004', '付款人账号：1234567890',
            '大写金额：壹仟贰佰叁拾肆元伍角',
        ]])
        with patch.object(self.module.requests, 'post', side_effect=AssertionError('Text PDF must stay local')):
            result = self.recognize(path)
        self.assertEqual(result['source'], 'pdf_text')
        self.assertEqual(result['fields'], {
            'payer_name': '上海甲园林有限公司', 'payee_name': '苏州乙苗木有限公司',
            'amount': '1234.50', 'payment_date': '2026-10-04',
            'receipt_number': 'BANK-20261004', 'bank_name': '中国工商银行',
        })
        self.assertEqual(Path(self.temp.name, 'receipt.pdf').read_bytes(), original)
        self.assertEqual(set(Path(self.temp.name).iterdir()), {Path(self.temp.name, 'receipt.pdf')})

    def test_labels_and_values_on_separate_lines_are_supported(self):
        path, _ = self.pdf([['付款人名称：', '甲有限公司', '收款人名称：', '乙有限公司',
                            '交易金额：', '120.5', '付款日期：', '2026/10/04', '回单号：', 'R-1']])
        self.assertEqual(self.recognize(path)['fields'], {
            'payer_name': '甲有限公司', 'payee_name': '乙有限公司', 'amount': '120.50',
            'payment_date': '2026-10-04', 'receipt_number': 'R-1',
        })

    def test_two_column_party_table_keeps_names_with_their_role(self):
        path, _ = self.pdf([[(40, 50, '付款人'), (470, 50, '收款人'),
                            (40, 80, '户名：'), (120, 80, '甲有限公司'),
                            (470, 80, '户名：'), (550, 80, '乙有限公司'),
                            (40, 110, '账号：123456'), (470, 110, '账号：789012'),
                            (40, 150, '交易金额：300.00'), (40, 180, '交易日期：2026-10-04')]])
        fields = self.recognize(path)['fields']
        self.assertEqual(fields['payer_name'], '甲有限公司')
        self.assertEqual(fields['payee_name'], '乙有限公司')
        self.assertEqual(fields['amount'], '300.00')

    def test_multiple_pages_use_first_page_and_warn_without_merging(self):
        path, _ = self.pdf([['付款人：甲公司', '收款人：乙公司', '交易金额：120.00'],
                            ['付款人：丙公司', '收款人：丁公司', '交易金额：999.00',
                             '回单编号：SECOND-ONLY']])
        result = self.recognize(path)
        self.assertEqual(result['fields']['amount'], '120.00')
        self.assertNotIn('receipt_number', result['fields'])
        self.assertTrue(any('第一页' in warning and '合并' in warning for warning in result['warnings']))

    def test_bank_serial_number_is_fallback_when_no_receipt_number_is_present(self):
        for index, (extra, expected) in enumerate([
            ([], 'BANK-A'), (['回单编号：RECEIPT-A'], 'RECEIPT-A'),
        ]):
            with self.subTest(extra=extra):
                path, _ = self.pdf([['付款人：甲公司', '收款人：乙公司', '交易金额：120.00',
                                    '银行流水号：BANK-A', *extra]], f'serial-{index}.pdf')
                fields = self.recognize(path)['fields']
                self.assertEqual(fields.get('receipt_number'), expected)
                self.assertEqual(fields.get('amount'), '120.00')

    def test_explicit_bank_label_after_serial_number_extracts_all_six_fields(self):
        for index, colon in enumerate([':', '：']):
            with self.subTest(colon=colon):
                path, _ = self.pdf([[
                    '付款人名称：甲有限公司', '收款人名称：乙有限公司',
                    '金额：360.50', '付款日期：2026-10-04',
                    '银行流水号：BANK-A', '银行' + colon + '测试银行',
                ]], f'bank-label-{index}.pdf')
                result = self.recognize(path)
                self.assertEqual(result['source'], 'pdf_text')
                self.assertEqual(result['fields'], {
                    'payer_name': '甲有限公司', 'payee_name': '乙有限公司',
                    'amount': '360.50', 'payment_date': '2026-10-04',
                    'receipt_number': 'BANK-A', 'bank_name': '测试银行',
                })

    def test_duplicate_receipts_even_with_identical_parties_are_not_guessed(self):
        path, _ = self.pdf([['中国工商银行电子回单', '付款人：甲公司', '收款人：乙公司', '金额：120.00',
                            '中国工商银行电子回单', '付款人：甲公司', '收款人：乙公司', '金额：120.00']])
        result = self.recognize(path)
        self.assertEqual(result['fields'], {})
        self.assertTrue(any('多个回单' in warning for warning in result['warnings']))

    def test_conflicting_amounts_reject_all_automatic_fields(self):
        path, _ = self.pdf([['付款人：甲公司', '收款人：乙公司', '小写金额：120.00', '交易金额：121.00']])
        result = self.recognize(path)
        self.assertEqual(result['fields'], {})
        self.assertTrue(any('金额' in warning and '冲突' in warning for warning in result['warnings']))

    def test_conflicting_names_reject_all_automatic_fields(self):
        path, _ = self.pdf([['付款人：甲公司', '付款人户名：丙公司', '收款人：乙公司', '金额：120.00']])
        self.assertEqual(self.recognize(path)['fields'], {})

    def test_matching_amount_aliases_and_fee_are_not_conflicts(self):
        path, _ = self.pdf([['付款人：甲公司', '收款人：乙公司', '交易金额：1,200.00',
                            '小写金额：￥1200.00元', '手续费：10.00']])
        self.assertEqual(self.recognize(path)['fields']['amount'], '1200.00')

    def test_multiple_amounts_with_one_invalid_value_are_not_guessed(self):
        path, _ = self.pdf([['付款人：甲公司', '收款人：乙公司',
                            '交易金额：120.00', '小写金额：121.001']])
        result = self.recognize(path)
        self.assertEqual(result['fields'], {})
        self.assertTrue(any('金额' in warning for warning in result['warnings']))

    def test_date_validation_and_print_date_never_replace_transaction_date(self):
        examples = [('20261004', '2026-10-04'), ('2026.10.04 14:20:31', '2026-10-04'),
                    ('2024年2月29日', '2024-02-29'), ('2026-02-30', None)]
        for index, (value, expected) in enumerate(examples):
            with self.subTest(value=value):
                path, _ = self.pdf([['付款人：甲公司', '金额：120.00', '交易日期：' + value,
                                    '打印日期：2026-10-05']], f'date-{index}.pdf')
                result = self.recognize(path)
                self.assertEqual(result['fields'].get('payment_date'), expected)

    def test_invalid_amounts_are_omitted_and_warned(self):
        for index, value in enumerate(['-120.00', '120.001', '1,20.00', 'NaN', '10000000000000000']):
            with self.subTest(value=value):
                path, _ = self.pdf([['付款人：甲公司', '收款人：乙公司', '金额：' + value]], f'amount-{index}.pdf')
                result = self.recognize(path)
                self.assertNotIn('amount', result['fields'])
                self.assertTrue(any('金额' in warning for warning in result['warnings']))

    def test_scanned_pdf_without_ocr_config_returns_actionable_error(self):
        _, png = self.png()
        with pymupdf.open() as doc:
            page = doc.new_page()
            page.insert_image(page.rect, stream=png)
            original = doc.tobytes()
        Path(self.temp.name, 'scan.pdf').write_bytes(original)
        with self.assertRaisesRegex(ValueError, '未配置.*OCR.*手工'):
            self.recognize('/uploads/scan.pdf')
        self.assertEqual(Path(self.temp.name, 'scan.pdf').read_bytes(), original)

    def test_image_without_config_returns_actionable_error(self):
        path, _ = self.png()
        with self.assertRaisesRegex(ValueError, '未配置.*OCR.*手工'):
            self.recognize(path, 'png')

    def test_ocr_uses_receipt_endpoint_and_maps_confident_documented_fields(self):
        path, original = self.png()
        words = {'标题': [self.word('中国农业银行电子回单')],
                 '付款人户名': [self.word('甲公司')], '收款人户名': [self.word('乙公司')],
                 '小写金额': [self.word('￥360.20元')], '交易日期': [self.word('2026-10-04')],
                 '回单编号': [self.word('OCR-1')], '流水号': [self.word('TRANS-1')],
                 '付款人开户银行': [self.word('农业银行甲支行')],
                 '收款人开户银行': [self.word('建设银行乙支行')],
                 '付款人账号': [self.word('12345')], '收款人账号': [self.word('67890')],
                 '大写金额': [self.word('叁佰陆拾元贰角')], '摘要': [self.word('苗木款')],
                 '用途': [self.word('货款')]}
        with patch.dict(os.environ, {'BAIDU_OCR_API_KEY': 'test-api-key', 'BAIDU_OCR_SECRET_KEY': 'test-secret-key'}):
            with self.ocr_http(words) as post:
                result = self.recognize(path, 'png')
        self.assertEqual(result['source'], 'ocr')
        self.assertEqual(result['fields'], {'payer_name': '甲公司', 'payee_name': '乙公司',
                                         'amount': '360.20', 'payment_date': '2026-10-04',
                                         'receipt_number': 'OCR-1', 'bank_name': '中国农业银行'})
        calls = post.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[1].args[0].endswith('/bank_receipt_new'))
        for call in calls:
            self.assertIsNot(call.kwargs.get('verify'), False)
            self.assertIs(call.kwargs.get('allow_redirects'), False)
            self.assertLessEqual(sum(call.kwargs['timeout']), 12)
        self.assertEqual(calls[1].kwargs['data']['probability'], 'true')
        self.assertEqual(Path(self.temp.name, 'receipt.png').read_bytes(), original)

    def test_ocr_repeated_names_or_conflicting_amounts_are_not_guessed(self):
        path, _ = self.png()
        examples = [
            {'付款人户名': [self.word('同名公司'), self.word('同名公司')], '小写金额': [self.word('120.00')]},
            {'付款人户名': [self.word('甲公司')], '小写金额': [self.word('120.00'), self.word('121.00')]},
        ]
        with patch.dict(os.environ, {'BAIDU_OCR_API_KEY': 'k', 'BAIDU_OCR_SECRET_KEY': 's'}):
            for words in examples:
                with self.subTest(words=words), self.ocr_http(words):
                    result = self.recognize(path, 'png')
                    self.assertEqual(result['fields'], {})
                    self.assertTrue(result['warnings'])

    def test_ocr_low_or_missing_confidence_is_not_returned_as_trusted(self):
        path, _ = self.png()
        words = {'付款人户名': [self.word('低可信公司', average=0.65)],
                 '收款人户名': [{'word': '无置信度公司'}], '小写金额': [self.word('120.00')]}
        with patch.dict(os.environ, {'BAIDU_OCR_API_KEY': 'k', 'BAIDU_OCR_SECRET_KEY': 's'}), self.ocr_http(words):
            result = self.recognize(path, 'png')
        self.assertEqual(result['fields'], {'amount': '120.00'})
        self.assertTrue(any('置信度' in warning for warning in result['warnings']))

    def test_ocr_nonfinite_or_out_of_range_confidence_is_not_trusted(self):
        path, _ = self.png()
        words = {'付款人户名': [self.word('无效置信度公司', average=float('inf'))],
                 '收款人户名': [self.word('超过范围公司', minimum=1.5)],
                 '小写金额': [self.word('120.00')]}
        with patch.dict(os.environ, {'BAIDU_OCR_API_KEY': 'k', 'BAIDU_OCR_SECRET_KEY': 's'}), self.ocr_http(words):
            result = self.recognize(path, 'png')
        self.assertEqual(result['fields'], {'amount': '120.00'})

    def test_ocr_errors_do_not_leak_credentials_or_provider_message(self):
        path, _ = self.png()
        secret_text = 'test-api-key test-secret-key test-token'
        errors = [requests.Timeout(secret_text), requests.ConnectionError(secret_text), ValueError(secret_text)]
        with patch.dict(os.environ, {'BAIDU_OCR_API_KEY': 'test-api-key', 'BAIDU_OCR_SECRET_KEY': 'test-secret-key'}):
            for error in errors:
                with self.subTest(error=type(error).__name__), patch.object(self.module.requests, 'post', side_effect=error):
                    with self.assertRaises(ValueError) as caught:
                        self.recognize(path, 'png')
                    self.assertIn('手工', str(caught.exception))
                    for secret in secret_text.split():
                        self.assertNotIn(secret, str(caught.exception))
            with self.ocr_http({}, token={'error': secret_text, 'error_description': secret_text}):
                with self.assertRaisesRegex(ValueError, '授权.*手工') as caught:
                    self.recognize(path, 'png')
                self.assertNotIn(secret_text, str(caught.exception))

    def test_ocr_json_decoder_error_never_exposes_response_text(self):
        path, _ = self.png()
        with patch.dict(os.environ, {'BAIDU_OCR_API_KEY': 'k', 'BAIDU_OCR_SECRET_KEY': 's'}), \
                patch.object(self.module.requests, 'post', return_value=Mock(
                    status_code=200, json=Mock(side_effect=ValueError('secret response with private-token')))):
            with self.assertRaisesRegex(ValueError, '手工') as caught:
                self.recognize(path, 'png')
        self.assertNotIn('private-token', str(caught.exception))

    def test_ocr_provider_error_and_malformed_response_are_actionable(self):
        path, _ = self.png()
        with patch.dict(os.environ, {'BAIDU_OCR_API_KEY': 'k', 'BAIDU_OCR_SECRET_KEY': 's'}):
            for response in ({'error_code': 17, 'error_msg': 'private-token'}, {'words_result': []}):
                with self.subTest(response=response), patch.object(self.module.requests, 'post', side_effect=[
                    Mock(status_code=200, json=Mock(return_value={'access_token': 'test-token'})),
                    Mock(status_code=200, json=Mock(return_value=response)),
                ]):
                    with self.assertRaisesRegex(ValueError, 'OCR.*手工') as caught:
                        self.recognize(path, 'png')
                    self.assertNotIn('private-token', str(caught.exception))

    def test_ocr_wall_clock_budget_returns_even_when_transport_is_stalled(self):
        path, _ = self.png()
        release = threading.Event()
        def stalled(*args, **kwargs):
            release.wait(1)
            raise requests.Timeout('do not expose this')
        try:
            with patch.dict(os.environ, {'BAIDU_OCR_API_KEY': 'k', 'BAIDU_OCR_SECRET_KEY': 's'}), \
                    patch.object(self.module, 'OCR_TOTAL_SECONDS', 0.05), \
                    patch.object(self.module.requests, 'post', side_effect=stalled):
                start = time.monotonic()
                with self.assertRaisesRegex(ValueError, '超时.*手工'):
                    self.recognize(path, 'png')
                self.assertLess(time.monotonic() - start, 0.5)
        finally:
            release.set()

    def test_safe_original_reader_rejects_path_escape_and_remote_address(self):
        self.pdf([['金额：1.00']])
        for path in ['/uploads/../outside.pdf', 'http://127.0.0.1/private.pdf']:
            with self.subTest(path=path), self.assertRaises(BadRequest):
                self.recognize(path)

    def test_corrupt_and_unsupported_files_return_manual_fill_error(self):
        Path(self.temp.name, 'broken.pdf').write_bytes(b'not a PDF')
        with self.assertRaisesRegex(ValueError, 'PDF.*手工'):
            self.recognize('/uploads/broken.pdf')
        with self.assertRaisesRegex(ValueError, '格式.*手工'):
            self.recognize('/uploads/receipt.exe', 'exe')


if __name__ == '__main__':
    unittest.main()
