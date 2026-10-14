"""Match an original to an existing invoice without rewriting invoice facts."""
from sqlalchemy import func, or_

from pear_admin.extensions import db
from pear_admin.orms import MaterialInvoiceORM, MaterialInboundORM, MaterialOutboundORM, MaterialInventoryORM


def clean(value):
    return '' if value is None or str(value).strip() in ('', '--', '-', '无') else str(value).strip()


def find_existing_original_target(ocr, exclude_id=None):
    number, code = clean(ocr.get('invoice_number')), clean(ocr.get('invoice_code'))
    if not number:
        return None
    query = MaterialInvoiceORM.query.filter(func.trim(MaterialInvoiceORM.invoice_number) == number)
    if exclude_id is not None:
        query = query.filter(MaterialInvoiceORM.id != exclude_id)
    rows = query.all()
    digital = len(number) == 20 and number.isdigit()
    if not digital and code:
        exact = [row for row in rows if clean(row.invoice_code) == code]
        rows = exact or [row for row in rows if not clean(row.invoice_code)]
    if len(rows) > 1:
        raise ValueError(f'发票号 {number} 匹配到多条记录，请人工核对后补充原件')
    if not rows:
        return None
    target = rows[0]
    if not digital and clean(target.invoice_code) and not code:
        raise ValueError('未识别出传统发票代码，无法确定原件归属，请上传清晰原件后重试')
    return target


def validate_original_target(target, ocr):
    for field, label in [('buyer_tax_num', '购买方税号'), ('seller_tax_num', '销售方税号')]:
        stored, incoming = clean(getattr(target, field)), clean(ocr.get(field))
        if stored and incoming and stored.upper() != incoming.upper():
            raise ValueError(f'票号已存在，但{label}不一致，请核对原件')


def attach_original(target, file_path, file_name, file_type):
    # The conditional write also protects existing originals during concurrent uploads.
    changed = MaterialInvoiceORM.query.filter(
        MaterialInvoiceORM.id == target.id,
        or_(MaterialInvoiceORM.file_path.is_(None), func.trim(MaterialInvoiceORM.file_path) == ''),
    ).update({'file_path': file_path, 'file_name': file_name, 'file_type': file_type}, synchronize_session=False)
    if changed != 1:
        raise ValueError('该发票已有关联原件，保留已有原件，请人工核对')
    db.session.expire(target)


def transfer_pending_original(target, pending):
    attach_original(target, pending.file_path, pending.file_name, pending.file_type)
    for payment in list(pending.related_pays):
        if target not in payment.invoices:
            payment.invoices.append(target)
        payment.invoices.remove(pending)
    for model, field in [(MaterialInboundORM, 'invoice_id'), (MaterialOutboundORM, 'invoice_id'),
                         (MaterialInventoryORM, 'latest_invoice_id')]:
        column = getattr(model, field)
        db.session.query(model).filter(column == pending.id).update({field: target.id}, synchronize_session='fetch')
    db.session.delete(pending)
