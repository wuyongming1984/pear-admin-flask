"""Collect payment receipts; links change only on explicit user requests."""
import hashlib
import re
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload
from werkzeug.exceptions import HTTPException

from pear_admin.extensions import db, oss
from pear_admin.invoice_links import selected_ids, same_company
from pear_admin.invoice_preview import render_pdf_page, MAX_FILE_BYTES
from pear_admin.orms import PaymentReceiptORM, PayORM, OrderORM, ProjectORM, SupplierORM, PayerORM
from ._system_validation import validated, payload

payment_receipts_api = Blueprint('payment_receipts', __name__, url_prefix='/payment-receipts')
TEXT_FIELDS = {'receipt_number': 128, 'payer_name': 255, 'payee_name': 255, 'bank_name': 255, 'remarks': 4000}


def payment_options():
    return (joinedload(PayORM.payer), joinedload(PayORM.payee_supplier),
            joinedload(PayORM.order).joinedload(OrderORM.project))


def receipts_query():
    return db.select(PaymentReceiptORM).options(
        selectinload(PaymentReceiptORM.payments).options(*payment_options()))


def receipt(identity):
    row = db.session.scalar(receipts_query().where(PaymentReceiptORM.id == identity))
    if row is None:
        raise ValueError('回单不存在或已删除，请刷新列表')
    return row


def payment_json(pay):
    return {
        'id': pay.id, 'pay_number': pay.pay_number,
        'payer_name': pay.payer.name if pay.payer else '',
        'payee_supplier_name': pay.payee_supplier.name if pay.payee_supplier else '',
        'project_name': pay.order.project.project_name if pay.order and pay.order.project else '',
        'order_number': pay.order.order_number if pay.order else '',
        'current_payment_amount': str(pay.current_payment_amount or 0),
        'payment_purpose': pay.payment_purpose or '',
        'create_at': str(pay.create_at or '')[:10],
    }


def receipt_json(row):
    return {
        'id': row.id, **{key: getattr(row, key) or '' for key in TEXT_FIELDS},
        'payment_date': row.payment_date.isoformat() if row.payment_date else '',
        'amount': str(row.amount) if row.amount is not None else None,
        'file_name': row.file_name, 'file_type': row.file_type,
        'file_path': row.file_path, 'file_url': oss.generate_signed_url(row.file_path) or row.file_path,
        'file_size': row.file_size, 'create_at': str(row.create_at),
        'payments': [payment_json(pay) for pay in sorted(row.payments, key=lambda p: p.id, reverse=True)],
    }


def metadata(data):
    result = {}
    for key, maximum in TEXT_FIELDS.items():
        if key in data:
            value = data[key] or ''
            if not isinstance(value, str) or len(value.strip()) > maximum:
                raise ValueError(f'{key} 内容过长或格式无效')
            result[key] = value.strip()
    if 'payment_date' in data:
        value = data['payment_date']
        if value in ('', None):
            result['payment_date'] = None
        else:
            if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                raise ValueError('付款日期格式应为 YYYY-MM-DD')
            try:
                result['payment_date'] = date.fromisoformat(value)
            except ValueError:
                raise ValueError('请输入有效的付款日期')
    if 'amount' in data:
        value = data['amount']
        if value in ('', None):
            result['amount'] = None
        else:
            try:
                amount = Decimal(str(value))
                if not amount.is_finite() or amount < 0 or amount >= Decimal('10000000000000000'):
                    raise ValueError('回单金额超出有效范围')
                if amount != amount.quantize(Decimal('0.01')):
                    raise ValueError('回单金额最多保留两位小数')
            except InvalidOperation:
                raise ValueError('请输入有效的回单金额')
            result['amount'] = amount
    return result


@payment_receipts_api.get('')
@jwt_required()
@validated
def list_receipts():
    query = receipts_query().order_by(PaymentReceiptORM.id.desc())
    keyword = (request.args.get('q') or '').strip()[:100]
    if keyword:
        query = query.where(or_(*(getattr(PaymentReceiptORM, key).contains(keyword, autoescape=True)
                                 for key in ('receipt_number', 'payer_name', 'payee_name', 'bank_name', 'file_name', 'remarks'))))
    payment_id = request.args.get('payment_id', type=int)
    if payment_id:
        query = query.where(PaymentReceiptORM.payments.any(id=payment_id))
    status = request.args.get('linked')
    if status == 'linked':
        query = query.where(PaymentReceiptORM.payments.any())
    elif status == 'unlinked':
        query = query.where(~PaymentReceiptORM.payments.any())
    page = max(1, request.args.get('page', 1, type=int))
    limit = min(100, max(1, request.args.get('limit', 20, type=int)))
    batch = db.paginate(query, page=page, per_page=limit, error_out=False)
    return {'code': 0, 'data': [receipt_json(row) for row in batch.items], 'count': batch.total}


@payment_receipts_api.route('/<int:identity>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
@validated
def receipt_detail(identity):
    row = receipt(identity)
    if request.method == 'DELETE':
        db.session.delete(row)
        db.session.commit()
        return {'code': 0, 'msg': '回单记录已删除，付款单及原文件已保留'}
    if request.method == 'PUT':
        values = metadata(payload())
        for key, value in values.items():
            setattr(row, key, value)
        db.session.commit()
    return {'code': 0, 'msg': '保存成功', 'data': receipt_json(row)}


@payment_receipts_api.post('/upload')
@jwt_required()
@validated
def upload_receipt():
    file = request.files.get('file')
    if not file or not file.filename:
        raise ValueError('请选择回单文件')
    original = file.filename.replace('\\', '/').rsplit('/', 1)[-1]
    extension = Path(original).suffix.lower().lstrip('.')
    if extension not in ('pdf', 'png', 'jpg', 'jpeg', 'webp'):
        raise ValueError('支持 PDF、PNG、JPG 和 WebP 回单文件')
    content = file.stream.read(MAX_FILE_BYTES + 1)
    if not content or len(content) > MAX_FILE_BYTES:
        raise ValueError('回单文件为空或超过 20 MB')
    try:
        if extension == 'pdf':
            import pymupdf
            with pymupdf.open(stream=content, filetype='pdf') as document:
                if document.needs_pass or document.page_count < 1:
                    raise ValueError('PDF 已加密或没有可预览页面')
        else:
            from PIL import Image
            with Image.open(BytesIO(content)) as image:
                expected = {'png': 'PNG', 'jpg': 'JPEG', 'jpeg': 'JPEG', 'webp': 'WEBP'}[extension]
                if image.format != expected:
                    raise ValueError('文件扩展名与图片格式不一致')
                image.verify()
    except Exception:
        raise ValueError('回单文件损坏、已加密或格式不正确')
    digest = hashlib.sha256(content).hexdigest()
    existing = db.session.scalar(receipts_query().where(PaymentReceiptORM.file_hash == digest))
    if existing:
        return {'code': 0, 'msg': '该文件已收集，已返回原回单', 'data': {**receipt_json(existing), 'reused': True}}
    safe_name = re.sub(r'[^\w.\-\u4e00-\u9fff]', '_', Path(original).stem)[:140] + '.' + extension
    key = f'payment_receipts/{uuid.uuid4().hex}_{safe_name}'
    target = None
    if oss.bucket:
        file_path = oss.upload_file(BytesIO(content), filename=key)
    else:
        target = Path(current_app.config['UPLOAD_FOLDER']) / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        file_path = '/uploads/' + key
    row = PaymentReceiptORM(file_name=original[:255], file_path=file_path, file_type=extension,
                            file_size=len(content), file_hash=digest)
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if target:
            target.unlink(missing_ok=True)
        existing = db.session.scalar(receipts_query().where(PaymentReceiptORM.file_hash == digest))
        if not existing:
            raise
        return {'code': 0, 'msg': '该文件已收集', 'data': {**receipt_json(existing), 'reused': True}}
    return {'code': 0, 'msg': '回单已收集，请完善信息并关联付款单', 'data': receipt_json(row)}


def payments_query(keyword):
    query = db.select(PayORM).options(*payment_options()).order_by(PayORM.id.desc())
    if keyword:
        suppliers = db.select(SupplierORM.id).where(SupplierORM.name.contains(keyword, autoescape=True))
        payers = db.select(PayerORM.id).where(PayerORM.name.contains(keyword, autoescape=True))
        projects = db.select(ProjectORM.id).where(ProjectORM.project_name.contains(keyword, autoescape=True))
        orders = db.select(OrderORM.id).where(or_(OrderORM.order_number.contains(keyword, autoescape=True),
                                                 OrderORM.project_id.in_(projects)))
        query = query.where(or_(PayORM.pay_number.contains(keyword, autoescape=True),
                               PayORM.payment_purpose.contains(keyword, autoescape=True),
                               PayORM.payee_supplier_id.in_(suppliers), PayORM.payer_supplier_id.in_(payers),
                               PayORM.order_id.in_(orders)))
    return query


@payment_receipts_api.route('/<int:identity>/payments', methods=['GET', 'POST'])
@jwt_required()
@validated
def receipt_payments(identity):
    row = receipt(identity)
    if request.method == 'POST':
        # Serialize association changes for the same receipt in MySQL.
        db.session.execute(db.select(PaymentReceiptORM.id).where(PaymentReceiptORM.id == identity).with_for_update())
        db.session.expire(row, ['payments'])
        ids = selected_ids(payload().get('payment_ids'))
        payments = list(db.session.scalars(payments_query('').where(PayORM.id.in_(ids)))) if ids else []
        if len(payments) != len(ids):
            raise ValueError('所选付款单不存在，请刷新后重试')
        existing = {pay.id for pay in row.payments}
        row.payments.extend(pay for pay in payments if pay.id not in existing)
        db.session.commit()
    keyword = (request.args.get('q') or '').strip()[:100]
    query = payments_query(keyword).where(~PayORM.payment_receipts.any(id=identity))
    batch = db.paginate(query, page=max(1, request.args.get('page', 1, type=int)), per_page=20, error_out=False)
    candidates = [dict(payment_json(pay), recommended=same_company(row.payee_name, pay.payee_supplier.name if pay.payee_supplier else '')) for pay in batch.items]
    return {'code': 0, 'data': {'linked': [payment_json(pay) for pay in row.payments],
                               'candidates': candidates, 'count': batch.total}}


@payment_receipts_api.delete('/<int:identity>/payments/<int:payment_id>')
@jwt_required()
@validated
def unlink_payment(identity, payment_id):
    row = receipt(identity)
    pay = next((pay for pay in row.payments if pay.id == payment_id), None)
    if pay:
        row.payments.remove(pay)
        db.session.commit()
    return {'code': 0, 'msg': '已解除关联'}


@payment_receipts_api.get('/<int:identity>/preview-page')
@jwt_required()
@validated
def preview_receipt(identity):
    row = receipt(identity)
    if row.file_type != 'pdf':
        raise ValueError('此回单不是 PDF 文件')
    try:
        data = render_pdf_page(row.file_path, request.args.get('page', 1, type=int))
        response = jsonify(code=0, data=data)
    except HTTPException as error:
        response = jsonify(code=-1, msg=error.description)
        response.status_code = error.code
    response.headers['Cache-Control'] = 'private, no-store'
    return response
