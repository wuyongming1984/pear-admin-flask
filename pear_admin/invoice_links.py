"""Shared identity matching and validation for invoice/payment relationships."""
import unicodedata

from pear_admin.extensions import db
from pear_admin.orms import MaterialInvoiceORM


def company_key(name):
    return ''.join(unicodedata.normalize('NFKC', name or '').split()).casefold()


def same_company(seller, payee):
    key = company_key(seller)
    return bool(key) and key == company_key(payee)


def selected_ids(values):
    if not isinstance(values, list) or len(values) > 500:
        raise ValueError('请选择有效的关联记录列表（最多 500 条）')
    result = []
    for value in values:
        if isinstance(value, bool) or not str(value).isascii() or not str(value).isdigit() or int(value) <= 0:
            raise ValueError('关联记录 ID 格式错误')
        if int(value) not in result:
            result.append(int(value))
    return result


def payment_invoices(values):
    """Validate explicit user choices; seller matching is only a recommendation."""
    ids = selected_ids(values)
    invoices = list(db.session.scalars(db.select(MaterialInvoiceORM).where(MaterialInvoiceORM.id.in_(ids)))) if ids else []
    if len(invoices) != len(ids):
        raise ValueError('所选发票不存在，请刷新后重试')
    return invoices
