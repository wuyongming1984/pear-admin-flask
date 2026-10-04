"""Conservative, read-only suggestions for a single bank payment receipt.

Text PDFs stay local. Images/scans use the optional bank-receipt OCR endpoint,
never the VAT-invoice recognizer. No database writes or original-file rewrites.
"""
import base64
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
import os
from queue import Empty, Queue
import re
import threading
import time
import unicodedata

import pymupdf
import requests

from pear_admin.invoice_preview import read_original


OCR_TOTAL_SECONDS = 24
_TOKEN_URL = 'https://aip.baidubce.com/oauth/2.0/token'
_RECEIPT_URL = 'https://aip.baidubce.com/rest/2.0/ocr/v1/bank_receipt_new'
_FIELD_NAMES = {
    'payer_name': '付款人', 'payee_name': '收款人', 'amount': '金额',
    'payment_date': '付款日期', 'receipt_number': '回单编号', 'bank_name': '银行名称',
}
_LABELS = {
    'payer_name': ('付款人户名', '付款人名称', '付款人姓名', '付款单位名称', '付款方户名',
                   '汇款人户名', '汇款人名称', '付款单位', '付款方', '汇款人', '付款人'),
    'payee_name': ('收款人户名', '收款人名称', '收款人姓名', '收款单位名称', '收款方户名',
                   '收款单位', '收款方', '收款人'),
    'amount': ('金额(小写)', '交易金额(小写)', '小写金额', '付款金额', '支付金额',
               '转账金额', '交易金额', '金额小写', '金额'),
    'payment_date': ('交易日期', '付款日期', '支付日期', '转账日期', '交易时间', '付款时间'),
    'receipt_number': ('电子回单编号', '回单编号', '回单号码', '回单号', '凭证编号', '凭证号', '银行流水号'),
    'bank_name': ('银行名称', '回单银行', '出具银行', '银行:'),
}
# These labels stop a value but are not mapped to business metadata. In
# particular, account numbers, fees, print dates and either party's bank cannot
# be confused with the transaction amount/date or issuing bank.
_IGNORED_LABELS = (
    '付款人开户银行', '收款人开户银行', '付款人开户行', '收款人开户行',
    '付款人账号', '收款人账号', '付款账号', '收款账号', '大写金额', '金额(大写)',
    '金额大写', '人民币大写', '人民币(大写)', '开户银行', '开户行', '账号', '账户',
    '户名', '名称', '手续费', '打印日期', '打印时间', '记账日期',
    '业务流水号', '交易流水号', '流水号', '币种', '摘要', '用途', '备注', '附言',
    '电子回单', '银行回单', '转账凭证',
)
_LABEL_FIELDS = {label: field for field, labels in _LABELS.items() for label in labels}
_LABEL_PATTERN = re.compile('|'.join(re.escape(label) for label in sorted(
    set(_LABEL_FIELDS) | set(_IGNORED_LABELS), key=len, reverse=True)))
_OCR_FIELDS = {
    '付款人户名': 'payer_name', '收款人户名': 'payee_name', '小写金额': 'amount',
    '交易日期': 'payment_date', '回单编号': 'receipt_number', '标题': 'bank_name',
}


class _OCRFailure(ValueError):
    """Messages produced locally and safe to display without provider data."""


def _normalize(value):
    return unicodedata.normalize('NFKC', value).replace('\u00a0', ' ').strip()


def _amount(value):
    text = re.sub(r'\s+', '', _normalize(value))
    match = re.fullmatch(r'(?:人民币|RMB|CNY)?[¥￥]?([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)'
                         r'(?:\.([0-9]{1,2}))?(?:元|圆)?', text, re.IGNORECASE)
    if not match:
        return None
    try:
        amount = Decimal(match.group(1).replace(',', '') + '.' + (match.group(2) or '00'))
        if not amount.is_finite() or not 0 <= amount < Decimal('10000000000000000'):
            return None
        return format(amount.quantize(Decimal('0.01')), '.2f')
    except InvalidOperation:
        return None


def _payment_date(value):
    text = re.sub(r'\s+', ' ', _normalize(value))
    match = re.fullmatch(r'([0-9]{4})[-/.年]([0-9]{1,2})[-/.月]([0-9]{1,2})日?'
                         r'(?:[ T][0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?)?', text)
    if not match:
        match = re.fullmatch(r'([0-9]{4})([0-9]{2})([0-9]{2})', text)
    if not match:
        return None
    try:
        return date(*(int(part) for part in match.groups())).isoformat()
    except ValueError:
        return None


def _bank_from_title(value):
    text = re.sub(r'\s+', '', _normalize(value))
    if not re.search(r'回单|转账凭证', text):
        return None
    match = re.match(r'([\u4e00-\u9fff]{2,20}?银行)', text)
    return match.group(1) if match else None


def _clean_value(field, value):
    value = _normalize(value).strip(':：| ')
    if not value:
        return None
    if field == 'amount':
        return _amount(value)
    if field == 'payment_date':
        return _payment_date(value)
    if field == 'receipt_number':
        compact = re.sub(r'\s+', '', value)
        return compact if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]{0,99}', compact) else None
    compact = re.sub(r'\s+', '', value)
    if len(compact) > 200 or not re.search(r'[A-Za-z\u4e00-\u9fff]', compact):
        return None
    if field == 'bank_name' and '银行' not in compact:
        return None
    return compact


def _labelled_candidates(text):
    text = _normalize(text)
    matches = list(_LABEL_PATTERN.finditer(text))
    has_receipt_number = any(match.group() in _LABELS['receipt_number'][:-1] for match in matches)
    candidates = defaultdict(list)
    for index, match in enumerate(matches):
        field = _LABEL_FIELDS.get(match.group())
        if not field:
            continue
        if match.group() == '银行流水号' and has_receipt_number:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        value = text[match.end():end].strip(':：| \n\r\t')
        # A bare role is a table header if the next token is a generic field
        # label. Its value is resolved from the PDF's table coordinates below.
        if value:
            candidates[field].append(value)
    return candidates


def _table_parties(page):
    """Resolve generic 户名 cells under explicit payer/payee column headers."""
    lines = []
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines', []):
            text = ''.join(span['text'] for span in line['spans'])
            lines.append((line['bbox'][0], line['bbox'][1], _normalize(text)))
    lines.sort(key=lambda item: (round(item[1], 1), item[0]))
    headers = [(x, y, _LABEL_FIELDS[text.rstrip(':：')]) for x, y, text in lines
               if text.rstrip(':：') in ('付款人', '付款方', '付款单位', '汇款人',
                                        '收款人', '收款方', '收款单位')]
    candidates = defaultdict(list)
    for x, y, field in headers:
        peers = sorted(hx for hx, hy, _ in headers if abs(hy - y) < 5)
        position = peers.index(x)
        left = (peers[position - 1] + x) / 2 if position else x - 20
        right = peers[position + 1] - 10 if position + 1 < len(peers) else page.rect.width
        next_header = min((hy for hx, hy, _ in headers if hy > y + 5 and left <= hx < right),
                          default=y + 150)
        region = [(lx, ly, text) for lx, ly, text in lines
                  if left <= lx < right and y + 5 < ly < min(y + 150, next_header)]
        for lx, ly, text in region:
            match = re.match(r'^(?:户名|名称)\s*[:：]?\s*(.*)$', text)
            if not match:
                continue
            inline = match.group(1).strip()
            if inline:
                candidates[field].append(inline)
            else:
                row = [text for vx, vy, text in region if vx > lx and abs(vy - ly) < 5]
                if row:
                    candidates[field].append(''.join(row))
                else:
                    below = [item for item in region if ly + 5 < item[1] < ly + 35]
                    if len(below) == 1 and not _LABEL_PATTERN.search(below[0][2]):
                        candidates[field].append(below[0][2])
            break
    return candidates


def _resolve_candidates(candidates, warnings, repeated_parties=False):
    fields = {}
    ambiguous = False
    for field, values in candidates.items():
        cleaned = [_clean_value(field, value) for value in values]
        trusted = set(value for value in cleaned if value is not None)
        if len(trusted) > 1:
            warnings.append(f'{_FIELD_NAMES[field]}存在冲突，未自动填写，请核对原件并手工填写。')
            if field != 'bank_name':
                ambiguous = True
        elif len(trusted) == 1:
            fields[field] = trusted.pop()
        if any(value is None for value in cleaned):
            warnings.append(f'{_FIELD_NAMES[field]}格式无法确认，未采用无效值，请手工核对。')
            if field == 'amount' and len(values) > 1:
                warnings.append('同页存在多个金额且不能确认一致，未自动填写，请手工核对原件。')
                ambiguous = True
    if repeated_parties:
        warnings.append('同页疑似包含多个回单或重复付款/收款主体，未自动填写，请拆分原件或手工填写。')
        ambiguous = True
    return {} if ambiguous else fields


def _pdf_fields(page, warnings):
    text = page.get_text('text', sort=True)
    candidates = _labelled_candidates(text)
    for field, values in _table_parties(page).items():
        if not candidates[field]:
            candidates[field].extend(values)
    if not candidates['bank_name']:
        for line in text.splitlines():
            bank = _bank_from_title(line)
            if bank:
                candidates['bank_name'].append(bank)
    repeated = any(len(candidates[field]) > 1 for field in ('payer_name', 'payee_name'))
    titles = re.findall(r'(?:电子回单|银行回单|转账凭证)', text)
    fields = _resolve_candidates(candidates, warnings, repeated or len(titles) > 1)
    return fields, bool(any(candidates.values())), bool(repeated or len(titles) > 1)


def _post_json(url, *, deadline, **kwargs):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise _OCRFailure('回单 OCR 超时，请手工填写。')
    # Two calls, no retry: at most 3s connect + 8s read per call. The caller
    # also imposes one wall-clock deadline because requests read timeouts alone
    # do not bound DNS stalls or a response trickling bytes indefinitely.
    response = requests.post(url, timeout=(min(3, remaining / 2), min(8, remaining / 2)),
                             allow_redirects=False, **kwargs)
    try:
        if response.status_code != 200:
            raise _OCRFailure('回单 OCR 服务暂时不可用，请手工填写。')
        result = response.json()
        if not isinstance(result, dict):
            raise _OCRFailure('回单 OCR 返回格式异常，请手工填写。')
        return result
    finally:
        response.close()


def _request_receipt_ocr(image, api_key, secret_key, deadline):
    token = _post_json(_TOKEN_URL, deadline=deadline, data={
        'grant_type': 'client_credentials', 'client_id': api_key, 'client_secret': secret_key,
    })
    if not isinstance(token.get('access_token'), str) or not token['access_token']:
        raise _OCRFailure('回单 OCR 授权失败，请检查配置或手工填写。')
    # Documentation: https://cloud.baidu.com/doc/OCR/s/Plep1yzi9
    result = _post_json(_RECEIPT_URL, deadline=deadline,
                        params={'access_token': token['access_token']},
                        data={'image': base64.b64encode(image).decode('ascii'), 'probability': 'true'},
                        headers={'Content-Type': 'application/x-www-form-urlencoded'})
    if 'error_code' in result:
        raise _OCRFailure('回单 OCR 识别失败，请检查服务权限和额度或手工填写。')
    if not isinstance(result.get('words_result'), dict):
        raise _OCRFailure('回单 OCR 返回格式异常，请手工填写。')
    return result['words_result']


def _ocr_fields(image, warnings, deadline):
    api_key = os.getenv('BAIDU_OCR_API_KEY', '').strip()
    secret_key = os.getenv('BAIDU_OCR_SECRET_KEY', '').strip()
    if not api_key or not secret_key:
        raise ValueError('未配置回单 OCR，无法识别图片或扫描原件，请手工填写。')
    output = Queue(maxsize=1)
    cancelled = threading.Event()

    def run():
        try:
            result = _request_receipt_ocr(image, api_key, secret_key, deadline)
            if not cancelled.is_set():
                output.put((result, None))
        except requests.Timeout:
            if not cancelled.is_set():
                output.put((None, '回单 OCR 超时，请手工填写。'))
        except _OCRFailure as exc:
            if not cancelled.is_set():
                output.put((None, str(exc)))
        except Exception:
            # Provider/network exceptions may include key/token URLs. Never
            # forward their messages, raw response bodies or logs to callers.
            if not cancelled.is_set():
                output.put((None, '回单 OCR 服务暂时不可用，请手工填写。'))

    worker = threading.Thread(target=run, name='receipt-ocr', daemon=True)
    worker.start()
    try:
        words, error = output.get(timeout=max(0.001, deadline - time.monotonic()))
    except Empty:
        cancelled.set()
        raise ValueError('回单 OCR 超时，请手工填写。') from None
    if error:
        raise ValueError(error) from None
    candidates = defaultdict(list)
    repeated = False
    for label, field in _OCR_FIELDS.items():
        entries = words.get(label, [])
        if not isinstance(entries, list):
            warnings.append(f'OCR {_FIELD_NAMES[field]}格式异常，请手工核对。')
            continue
        values = [item for item in entries if isinstance(item, dict) and isinstance(item.get('word'), str)
                  and item['word'].strip()]
        if field in ('payer_name', 'payee_name', 'amount', 'receipt_number') and len(values) > 1:
            repeated = True
        for item in values:
            probability = item.get('probability')
            try:
                confident = (isinstance(probability, dict)
                             and 0.90 <= float(probability.get('average', 0)) <= 1
                             and 0.70 <= float(probability.get('min', 0)) <= 1)
            except (TypeError, ValueError):
                confident = False
            if not confident:
                warnings.append(f'OCR {_FIELD_NAMES[field]}置信度不足或缺失，未自动填写。')
                continue
            value = _bank_from_title(item['word']) if field == 'bank_name' else item['word']
            if value:
                candidates[field].append(value)
    fields = _resolve_candidates(candidates, warnings, repeated)
    warnings.append('OCR 结果供填写参考，请逐项核对原件后保存。')
    return fields


def recognize_receipt(file_path, file_type):
    """Return trusted field suggestions only, without saving them.

    ``fields`` is a subset of payer_name/payee_name/amount/payment_date/
    receipt_number/bank_name; amounts and dates are normalized strings.
    ``source`` is pdf_text or ocr; ``warnings`` is a list of Chinese messages.
    Ambiguous single-page documents return empty fields with warnings. Missing
    OCR config, invalid files and service failures raise a safe ``ValueError``;
    read_original's path/auth/storage HTTP exceptions are preserved.
    """
    deadline = time.monotonic() + OCR_TOTAL_SECONDS
    file_type = str(file_type or '').lower().lstrip('.')
    if file_type not in ('pdf', 'png', 'jpg', 'jpeg', 'bmp', 'webp'):
        raise ValueError('不支持的回单文件格式，请查看原件并手工填写。')
    data = read_original(file_path)
    warnings = []
    image = None
    if file_type == 'pdf':
        try:
            with pymupdf.open(stream=data, filetype='pdf') as doc:
                if doc.needs_pass or not doc.page_count:
                    raise ValueError('PDF 已加密或没有页面，请查看原件并手工填写。')
                if doc.page_count > 1:
                    warnings.append(f'原件有 {doc.page_count} 页，仅识别第一页，不合并其他页面，请逐页核对。')
                page = doc[0]
                fields, has_candidates, ambiguous = _pdf_fields(page, warnings)
                if fields or has_candidates or ambiguous:
                    if not fields and not ambiguous:
                        warnings.append('未提取到可信回单字段，请核对原件并手工填写。')
                    return {'fields': fields, 'source': 'pdf_text', 'warnings': list(dict.fromkeys(warnings))}
                # Only the first page is rendered, with a bounded raster size.
                longest = max(page.rect.width, page.rect.height)
                if longest <= 0:
                    raise ValueError('PDF 页面尺寸无效，请查看原件并手工填写。')
                pix = page.get_pixmap(matrix=pymupdf.Matrix(min(2, 2400 / longest),
                                                         min(2, 2400 / longest)),
                                      colorspace=pymupdf.csRGB, alpha=False)
                image = pix.tobytes('png')
        except (pymupdf.FileDataError, RuntimeError) as exc:
            raise ValueError('PDF 文件损坏或无法读取，请查看原件并手工填写。') from None
    else:
        try:
            # Decode in memory to validate the original and normalize formats
            # accepted by the receipt endpoint. Source bytes are never written.
            pix = pymupdf.Pixmap(data)
            if max(pix.width, pix.height) > 4096:
                raise ValueError('回单图片尺寸过大，请提供清晰单张回单或手工填写。')
            if min(pix.width, pix.height) < 15:
                raise ValueError('回单图片尺寸过小，请提供清晰单张回单或手工填写。')
            if pix.colorspace is None or pix.colorspace.n != 3:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            if pix.alpha:
                pix = pymupdf.Pixmap(pix, 0)
            image = pix.tobytes('png')
        except (RuntimeError, ValueError) as exc:
            if isinstance(exc, ValueError) and '手工填写' in str(exc):
                raise
            raise ValueError('回单图片无效或无法读取，请查看原件并手工填写。') from None
    if len(base64.b64encode(image)) > 4 * 1024 * 1024:
        raise ValueError('回单图片过大，无法进行 OCR，请查看原件并手工填写。')
    fields = _ocr_fields(image, warnings, deadline)
    if not fields:
        warnings.append('未提取到可信回单字段，请核对原件并手工填写。')
    return {'fields': fields, 'source': 'ocr', 'warnings': list(dict.fromkeys(warnings))}
