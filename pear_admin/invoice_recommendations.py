"""Read-only, explainable suggestions for the existing invoice/payment links."""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from itertools import combinations

from sqlalchemy import or_

from pear_admin.extensions import db
from pear_admin.invoice_links import company_key, same_company, selected_ids, supplier_company_name
from pear_admin.orms import MaterialInvoiceORM, OrderORM, PayORM, PayerORM, ProjectORM, SupplierORM
from pear_admin.orms.pay import pay_invoice_relation


ZERO = Decimal('0.00')
CENT = Decimal('0.01')
MAX_MONEY = Decimal('9999999999999999.99')
RESULT_LIMIT = 200
COMBINATION_LIMIT = 30


def money(value):
    return None if value is None else format(Decimal(value).quantize(CENT), '.2f')


def invoice_gross(invoice):
    if invoice.total_amount is None or invoice.tax_amount is None:
        return None
    return Decimal(invoice.total_amount) + Decimal(invoice.tax_amount)


def known_total(values):
    total = ZERO
    for value in values:
        if value is None:
            return None
        total += Decimal(value)
    return total


def remaining_amount(target, selected):
    return None if target is None or selected is None else target - selected


def positive(value):
    return value is not None and value > ZERO


def input_money(value, label):
    if value is None or value == '':
        return ZERO
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError(f'{label}必须为有效金额')
    try:
        number = Decimal(str(value))
        if not number.is_finite() or abs(number) > MAX_MONEY or number != number.quantize(CENT):
            raise ValueError(f'{label}必须为有限金额，最多两位小数')
        return number.quantize(CENT)
    except (InvalidOperation, TypeError):
        raise ValueError(f'{label}必须为有效金额') from None


def input_id(value, label, required=False):
    if value is None or value == '':
        if required:
            raise ValueError(f'请先选择{label}')
        return None
    if isinstance(value, bool) or not str(value).isascii() or not str(value).isdigit():
        raise ValueError(f'{label} ID 格式错误')
    result = int(value)
    if result <= 0 or result > 2147483647:
        raise ValueError(f'{label} ID 格式错误')
    return result


def input_date(value):
    if value is None or value == '':
        return None
    if not isinstance(value, str):
        raise ValueError('付款日期格式错误')
    for pattern in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            pass
    raise ValueError('付款日期格式错误')


def context(target, basis, selected):
    result = {'target_amount': money(target), 'amount_basis': basis,
        'selected_gross': money(selected), 'remaining': money(remaining_amount(target, selected))}
    reasons = []
    if target is None:
        reasons.append('发票净额或税额待核实，目标价税合计未知，已停止自动推荐')
    if selected is None:
        reasons.append('已选关联记录的金额待核实，选中合计及剩余金额未知，已停止自动推荐')
    if reasons:
        result['reasons'] = reasons
    return result


def company_score(left, right, reasons, label):
    if not left or not right:
        reasons.append(f'{label}信息不完整')
        return 0
    if company_key(left) == company_key(right) and same_company(left, right):
        reasons.append(f'{label}名称一致')
        return 60
    if same_company(left, right):
        reasons.append(f'{label}名称相近，请核对')
        return 40
    reasons.append(f'{label}名称不一致，请核对')
    return 0


def supporting_score(buyer, payer, candidate_project, target_project, candidate_date, target_date, reasons):
    score = 0
    if buyer and payer:
        if same_company(buyer, payer):
            score += 10
            reasons.append('购买方与付款单位相符')
        else:
            reasons.append('购买方与付款单位不同，请核对')
    else:
        reasons.append('购买方或付款单位未完善')
    cross_project = bool(target_project and candidate_project and target_project != candidate_project)
    if cross_project:
        reasons.append('关联项目不同，保留人工选择')
    elif target_project and candidate_project:
        score += 10
        reasons.append('关联项目一致')
    else:
        reasons.append('项目资料不完整')
    if candidate_date and target_date:
        distance = abs((candidate_date - target_date).days)
        if distance <= 30:
            score += 10
        elif distance <= 90:
            score += 5
        reasons.append(f'开票与付款日期相差 {distance} 天')
    else:
        reasons.append('开票或付款日期未完善')
    return score, cross_project


def amount_score(amount, remaining, reasons):
    if amount is None:
        reasons.append('金额待核实，无法计算价税合计或差额，保留人工选择')
        return 0, None
    if remaining is None:
        reasons.append('待匹配金额待核实，已停止自动推荐，保留人工选择')
        return 0, None
    if remaining <= ZERO:
        reasons.append('没有正的待匹配金额，保留人工选择')
        return 0, None
    difference = amount - remaining
    if difference == ZERO:
        reasons.append('金额与剩余目标一致')
        return 40, money(difference)
    reasons.append(f'与剩余目标差额 {money(difference)} 元')
    return (15 if abs(difference) <= remaining * Decimal('.01') else 0), money(difference)


def candidate_order(row):
    difference = row['amount_difference']
    return (not row['already_selected'], not row['can_recommend'],
        difference != '0.00', -row['score'], abs(Decimal(difference)) if difference is not None else Decimal('Infinity'),
        -row['id'])


def visible_candidates(rows):
    """Selected records never consume the allowance for new suggestions."""
    selected = [row for row in rows if row['already_selected']]
    unselected = [row for row in rows if not row['already_selected']]
    return selected + unselected[:RESULT_LIMIT], len(unselected) > RESULT_LIMIT


def suggest_combinations(rows, remaining, amount_key, id_key):
    if not positive(remaining):
        return []
    eligible = [row for row in rows if row['can_recommend']][:COMBINATION_LIMIT]
    proposals = []
    for size in (1, 2, 3):
        for group in combinations(eligible, size):
            total = sum((Decimal(row[amount_key]) for row in group), ZERO)
            difference = total - remaining
            if difference != ZERO:
                continue
            proposals.append((size, -sum(row['score'] for row in group),
                tuple(sorted(row['id'] for row in group)),
                {id_key: [row['id'] for row in group], 'total_gross': money(total),
                    'difference': money(difference), 'reasons': ['合计金额与剩余目标一致']}))
    proposals.sort(key=lambda value: value[:3])
    return [item[3] for item in proposals[:5]]


def payment_recommendations(data):
    if not isinstance(data, dict):
        raise ValueError('请求数据格式错误')
    sid = input_id(data.get('payee_supplier_id'), '收款单位', required=True)
    pid = input_id(data.get('payer_supplier_id'), '付款单位')
    oid = input_id(data.get('order_id'), '关联订单')
    pay_id = input_id(data.get('pay_id'), '付款单')
    current = input_money(data.get('current_payment_amount'), '本次付款金额')
    invoiced = input_money(data.get('invoice_amount'), '开票金额')
    paid_date = input_date(data.get('create_at'))
    ids = selected_ids(data.get('selected_invoice_ids', []))
    if any(i > 2147483647 for i in ids):
        raise ValueError('关联发票 ID 格式错误')
    supplier = db.session.execute(db.select(SupplierORM.name, SupplierORM.contact_person)
        .where(SupplierORM.id == sid)).first()
    if not supplier:
        raise ValueError('收款单位不存在，请重新选择')
    payee = supplier_company_name(supplier.name, supplier.contact_person)
    if not company_key(payee):
        raise ValueError('收款单位名称为空，请先完善资料')
    payer = db.session.scalar(db.select(PayerORM.name).where(PayerORM.id == pid)) if pid else None
    if pid and payer is None:
        raise ValueError('付款单位不存在')
    order = db.session.execute(db.select(OrderORM.id, OrderORM.project_id).where(OrderORM.id == oid)).first() if oid else None
    if oid and not order:
        raise ValueError('关联订单不存在')
    if pay_id and db.session.scalar(db.select(PayORM.id).where(PayORM.id == pay_id)) is None:
        raise ValueError('付款单不存在')
    if pay_id and 'selected_invoice_ids' not in data:
        ids = list(db.session.scalars(db.select(pay_invoice_relation.c.invoice_id).where(pay_invoice_relation.c.pay_id == pay_id)))
    selected = set(ids)
    model = MaterialInvoiceORM
    seller_names = db.session.scalars(db.select(model.seller_name).distinct()).all()
    matching_names = [name for name in seller_names if same_company(name, payee)]
    # Projection avoids invoice detail rows, OCR data and file signing.
    invoices = db.session.execute(db.select(model.id, model.invoice_number, model.invoice_code,
        model.invoice_date, model.seller_name, model.buyer_name, model.total_amount, model.tax_amount,
        model.project_id, model.invoice_type, model.invoice_name)
        .where(or_(model.seller_name.in_(matching_names), model.id.in_(ids)))).all()
    by_id = {row.id: row for row in invoices}
    if any(i not in by_id for i in ids):
        raise ValueError('所选发票不存在，请刷新后重试')
    matching = [row for row in invoices if row.id in selected or same_company(row.seller_name, payee)]
    linked = {}
    if matching:
        relationships = db.session.execute(db.select(pay_invoice_relation.c.invoice_id, PayORM.id, PayORM.pay_number)
            .join(PayORM, pay_invoice_relation.c.pay_id == PayORM.id)
            .where(pay_invoice_relation.c.invoice_id.in_([row.id for row in matching])).order_by(PayORM.id.desc())).all()
        for iid, linked_id, number in relationships:
            linked.setdefault(iid, []).append({'id': linked_id, 'pay_number': number})
    target = invoiced if invoiced > ZERO else max(current, ZERO)
    basis = 'invoice_amount' if invoiced > ZERO else 'current_payment_amount'
    selected_gross = known_total(invoice_gross(by_id[i]) for i in ids)
    remaining = remaining_amount(target, selected_gross)
    rows = []
    for invoice in matching:
        reasons = []
        score = company_score(invoice.seller_name, payee, reasons, '销售方与收款单位')
        extra, cross = supporting_score(invoice.buyer_name, payer, invoice.project_id,
            order.project_id if order else None, invoice.invoice_date, paid_date, reasons)
        gross = invoice_gross(invoice)
        extra_amount, difference = amount_score(gross, remaining, reasons)
        links = linked.get(invoice.id, [])
        elsewhere = [link for link in links if link['id'] != pay_id]
        red = '红' in (invoice.invoice_type or '') or '红' in (invoice.invoice_name or '')
        if invoice.id in selected:
            reasons.append('已选关联保留，推荐不会移除')
        if target <= ZERO:
            reasons.append('缺少正的付款金额或开票金额，保留人工选择')
        if elsewhere:
            reasons.append('已关联其他付款单，保留人工选择')
        if (gross is not None and gross <= ZERO) or red:
            reasons.append('非正金额或红字发票，保留人工选择')
        rows.append({'id': invoice.id, 'invoice_number': invoice.invoice_number,
            'invoice_code': invoice.invoice_code, 'invoice_date': invoice.invoice_date.isoformat() if invoice.invoice_date else None,
            'seller_name': invoice.seller_name or '', 'buyer_name': invoice.buyer_name or '',
            'total_amount': money(invoice.total_amount), 'tax_amount': money(invoice.tax_amount), 'gross_amount': money(gross),
            'score': score + extra + extra_amount, 'reasons': reasons, 'linked_payments': links,
            'already_selected': invoice.id in selected,
            'can_recommend': invoice.id not in selected and not elsewhere and not cross and positive(gross) and not red and positive(target) and positive(remaining),
            'amount_difference': difference})
    rows.sort(key=candidate_order)
    visible, truncated = visible_candidates(rows)
    return {'context': context(target, basis, selected_gross), 'candidates': visible,
        'combinations': suggest_combinations(visible, remaining, 'gross_amount', 'invoice_ids'),
        'total_count': len(rows), 'truncated': truncated, 'combination_limit': COMBINATION_LIMIT}


def invoice_payment_recommendations(invoice):
    """Keep linked/matched fields while adding scored, bounded reverse suggestions."""
    suppliers = db.session.execute(db.select(SupplierORM.id, SupplierORM.name, SupplierORM.contact_person)).all()
    matching = [row.id for row in suppliers if same_company(invoice.seller_name,
        supplier_company_name(row.name, row.contact_person))]
    linked_ids = db.select(pay_invoice_relation.c.pay_id).where(pay_invoice_relation.c.invoice_id == invoice.id)
    payments = db.session.execute(db.select(PayORM.id, PayORM.pay_number, PayORM.current_payment_amount,
        PayORM.payment_purpose, PayORM.create_at, SupplierORM.name.label('payee_name'), SupplierORM.contact_person,
        PayerORM.name.label('payer_name'), OrderORM.order_number, OrderORM.project_id, ProjectORM.project_name)
        .select_from(PayORM).outerjoin(SupplierORM, PayORM.payee_supplier_id == SupplierORM.id)
        .outerjoin(PayerORM, PayORM.payer_supplier_id == PayerORM.id)
        .outerjoin(OrderORM, PayORM.order_id == OrderORM.id).outerjoin(ProjectORM, OrderORM.project_id == ProjectORM.id)
        .where(or_(PayORM.payee_supplier_id.in_(matching), PayORM.id.in_(linked_ids))).order_by(PayORM.id.desc())).all()
    relationships = db.session.execute(db.select(pay_invoice_relation.c.pay_id, pay_invoice_relation.c.invoice_id)
        .where(pay_invoice_relation.c.pay_id.in_([row.id for row in payments]))).all() if payments else []
    links = {}
    for pid, iid in relationships:
        links.setdefault(pid, set()).add(iid)
    target = invoice_gross(invoice)
    selected = known_total(row.current_payment_amount for row in payments if invoice.id in links.get(row.id, set()))
    remaining = remaining_amount(target, selected)
    rows, linked_rows = [], []
    red = (target is not None and target <= ZERO) or '红' in (invoice.invoice_type or '') or '红' in (invoice.invoice_name or '')
    for payment in payments:
        summary = {'id': payment.id, 'pay_number': payment.pay_number,
            'payee_supplier_name': payment.payee_name or '', 'project_name': payment.project_name or '',
            'order_number': payment.order_number or '', 'current_payment_amount': money(payment.current_payment_amount),
            'payment_purpose': payment.payment_purpose or '', 'create_at': str(payment.create_at or '')[:10]}
        already = invoice.id in links.get(payment.id, set())
        if already:
            linked_rows.append(summary.copy())
        payee = supplier_company_name(payment.payee_name, payment.contact_person)
        if not same_company(invoice.seller_name, payee):
            continue
        reasons = []
        score = company_score(invoice.seller_name, payee, reasons, '销售方与收款单位')
        extra, cross = supporting_score(invoice.buyer_name, payment.payer_name, payment.project_id,
            invoice.project_id, invoice.invoice_date, payment.create_at.date() if payment.create_at else None, reasons)
        amount = None if payment.current_payment_amount is None else Decimal(payment.current_payment_amount)
        extra_amount, difference = amount_score(amount, remaining, reasons)
        elsewhere = links.get(payment.id, set()) - {invoice.id}
        if already:
            reasons.append('已关联付款单保留，推荐不会移除')
        if elsewhere:
            reasons.append('付款单已关联其他发票，保留人工选择')
        if (amount is not None and amount <= ZERO) or red:
            reasons.append('非正金额或红字发票，保留人工选择')
        summary.update(score=score + extra + extra_amount, reasons=reasons, amount_difference=difference,
            already_selected=already, can_recommend=not already and not elsewhere and not cross and positive(amount) and not red and positive(remaining))
        rows.append(summary)
    rows.sort(key=candidate_order)
    visible, truncated = visible_candidates(rows)
    return {'seller_name': invoice.seller_name or '', 'linked': linked_rows, 'matched': visible,
        'context': context(target, 'invoice_gross', selected),
        'combinations': suggest_combinations(visible, remaining, 'current_payment_amount', 'payment_ids'),
        'total_count': len(rows), 'truncated': truncated, 'combination_limit': COMBINATION_LIMIT}
