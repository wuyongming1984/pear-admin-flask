"""Shared identity matching and validation for invoice/payment relationships."""
import unicodedata
import re

from pear_admin.extensions import db
from pear_admin.orms import MaterialInvoiceORM


def supplier_company_name(name, contact):
    """Remove only a trailing annotation identifying this supplier's contact."""
    name = (name or '').strip()
    contact = (contact or '').strip()
    suffix = re.search(r'\s*[（(]([^（）()]*)[）)]$', name)
    if contact and suffix and suffix.group(1).strip() == contact:
        return name[:suffix.start()].rstrip()
    return name


def company_key(name):
    name = ''.join(unicodedata.normalize('NFKC', name or '').lower().split())
    name = re.sub(r'(公司|中心|商行|经营部|工作室)(?:\([^()]*\))+[。.,，]*$', r'\1', name)
    return ''.join(char for char in name if unicodedata.category(char)[0] in 'LN')


def same_company(seller, payee):
    """Candidate name match, not proof of company identity; users confirm links."""
    left, right = company_key(seller), company_key(payee)
    generic = r'(?:有限责任公司|有限公司|公司|集团|中心|商行|分公司|经营部|工作室)+'
    if not left or not right or re.fullmatch(generic, left) or re.fullmatch(generic, right):
        return False
    return left == right or (min(len(left), len(right)) >= 4 and (left in right or right in left))


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
