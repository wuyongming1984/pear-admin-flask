"""Explainable receipt/payment candidate ranking, without changing stored links."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from pear_admin.invoice_links import company_key, same_company


def _amount(value):
    if value is None or value == '' or isinstance(value, bool):
        return None
    try:
        amount = Decimal(str(value))
        return amount if amount.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def _date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value or '')[:10])
    except ValueError:
        return None


def receipt_payment_match(receipt, payment):
    """Return evidence for a matching pair, or None when no main field matches.

    A bank payment date and a payment-order date are different business facts;
    proximity adds a small amount of evidence but never creates a candidate.
    """
    reasons, conflicts = [], []
    score = 0
    matched, comparable = {}, {}
    pairs = (
        ('payee', '收款单位', receipt.payee_name,
         payment.payee_supplier.name if payment.payee_supplier else '', 35, 25),
        ('payer', '付款单位', receipt.payer_name,
         payment.payer.name if payment.payer else '', 20, 15),
    )
    for key, label, receipt_name, payment_name, exact_points, fuzzy_points in pairs:
        matched[key] = False
        comparable[key] = bool(company_key(receipt_name) and company_key(payment_name))
        if not comparable[key]:
            continue
        if same_company(receipt_name, payment_name):
            exact = company_key(receipt_name) == company_key(payment_name)
            score += exact_points if exact else fuzzy_points
            matched[key] = True
            reasons.append(f'{label}{"名称一致" if exact else "名称近似"}')
        else:
            conflicts.append(f'{label}不一致：回单“{receipt_name}”，付款单“{payment_name}”')
    receipt_amount = _amount(receipt.amount)
    payment_amount = _amount(payment.current_payment_amount)
    matched['amount'] = False
    comparable['amount'] = receipt_amount is not None and payment_amount is not None
    if comparable['amount']:
        if receipt_amount == payment_amount:
            score += 40
            matched['amount'] = True
            reasons.append(f'金额一致：{receipt_amount:.2f} 元')
        else:
            difference = abs(receipt_amount - payment_amount)
            conflicts.append(f'金额不一致：回单 {receipt_amount:.2f} 元，付款单 {payment_amount:.2f} 元，相差 {difference:.2f} 元')
    # One payer often pays many suppliers. It cannot outweigh two known conflicts.
    if comparable['payee'] and comparable['amount'] and not matched['payee'] and not matched['amount']:
        return None
    if not any(matched.values()):
        return None
    receipt_date = _date(receipt.payment_date)
    payment_date = _date(payment.create_at)
    if receipt_date is not None and payment_date is not None:
        days = abs((receipt_date - payment_date).days)
        if days <= 7:
            score += 5
            reasons.append(f'回单日期与付款单日期相差 {days} 天（仅作辅助，付款单日期不代表银行实际付款日期）')
    if conflicts:
        level = 'low'
    elif matched['payee'] and matched['amount']:
        level = 'high'
    elif score >= 35:
        level = 'medium'
    else:
        level = 'low'
    return {'match_score': score, 'match_level': level,
            'match_reasons': reasons, 'match_conflicts': conflicts,
            'recommended': level in ('high', 'medium')}


def rank_candidates(rows, matcher, page, page_size=20):
    """Score all rows first, keep ambiguities, then page the stable ranking."""
    ranked = []
    for row in rows:
        evidence = matcher(row)
        if evidence is not None:
            ranked.append((row, evidence))
    levels = {'high': 2, 'medium': 1, 'low': 0}
    ranked.sort(key=lambda pair: (levels[pair[1]['match_level']], pair[1]['match_score'], pair[0].id), reverse=True)
    start = (max(1, page) - 1) * page_size
    return ranked[start:start + page_size], len(ranked)


def matching_hint(receipt=None, payment=None):
    """Guide completion of missing source fields without assuming they are zero."""
    missing = []
    if receipt is not None:
        values = ((receipt.payee_name, '收款单位'), (receipt.payer_name, '付款单位'),
                  (_amount(receipt.amount), '金额'), (receipt.payment_date, '付款日期'))
    else:
        values = ((payment.payee_supplier.name if payment.payee_supplier else '', '收款单位'),
                  (payment.payer.name if payment.payer else '', '付款单位'),
                  (_amount(payment.current_payment_amount), '金额'))
    for value, label in values:
        if value is None or value == '':
            missing.append(label)
    hint = f'{"回单" if receipt is not None else "付款单"}缺少{"、".join(missing)}，完善后可提高匹配准确度。' if missing else ''
    return hint + '智能候选综合比较收款单位、金额和付款单位；日期仅作辅助。同分记录请逐项核对并勾选确认。'
