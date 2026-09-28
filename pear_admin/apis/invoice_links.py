"""Append invoice/payment links without replacing other linked invoices."""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from sqlalchemy.orm import selectinload

from pear_admin.extensions import db
from pear_admin.orms import MaterialInvoiceORM, PayORM, SupplierORM, OrderORM
from pear_admin.invoice_links import same_company, selected_ids

invoice_links_api = Blueprint('invoice_links', __name__, url_prefix='/invoice-links')


def payment_summary(pay):
    return {
        'id': pay.id, 'pay_number': pay.pay_number,
        'payee_supplier_name': pay.payee_supplier.name if pay.payee_supplier else '',
        'project_name': pay.order.project.project_name if pay.order and pay.order.project else '',
        'order_number': pay.order.order_number if pay.order else '',
        'current_payment_amount': str(pay.current_payment_amount or 0),
        'payment_purpose': pay.payment_purpose or '',
        'create_at': str(pay.create_at or '')[:10],
    }


def payments_query():
    return db.select(PayORM).options(selectinload(PayORM.payee_supplier), selectinload(PayORM.order).selectinload(OrderORM.project))


def link_data(invoice):
    # Read only names first; fetch details solely for matching payees and linked IDs.
    suppliers = db.session.execute(db.select(SupplierORM.id, SupplierORM.name)).all()
    matching = [sid for sid, name in suppliers if same_company(invoice.seller_name, name)]
    matched = list(db.session.scalars(payments_query().where(PayORM.payee_supplier_id.in_(matching)).order_by(PayORM.id.desc()))) if matching else []
    linked = list(db.session.scalars(payments_query().where(PayORM.invoices.any(id=invoice.id)).order_by(PayORM.id.desc())))
    return {'seller_name': invoice.seller_name or '', 'linked': [payment_summary(p) for p in linked], 'matched': [payment_summary(p) for p in matched]}


@invoice_links_api.route('/invoices/<int:invoice_id>/payments', methods=['GET', 'POST'])
@jwt_required()
def invoice_payments(invoice_id):
    query = db.select(MaterialInvoiceORM).where(MaterialInvoiceORM.id == invoice_id)
    if request.method == 'POST':
        query = query.with_for_update()
    invoice = db.session.scalar(query)
    if not invoice:
        return {'code': -1, 'msg': '发票不存在'}, 404
    if request.method == 'POST':
        data = request.get_json(silent=True)
        try:
            ids = selected_ids(data.get('payment_ids') if isinstance(data, dict) else None)
            payments = list(db.session.scalars(payments_query().where(PayORM.id.in_(ids)))) if ids else []
            if len(payments) != len(ids):
                raise ValueError('所选付款单不存在，请刷新后重试')
            existing = {pay.id for pay in invoice.related_pays}
            for pay in payments:
                if pay.id not in existing and not same_company(invoice.seller_name, pay.payee_supplier.name if pay.payee_supplier else ''):
                    raise ValueError(f'付款单 {pay.pay_number} 的收款单位与发票销售方不匹配')
            invoice.related_pays.extend(pay for pay in payments if pay.id not in existing)
            db.session.commit()
        except ValueError as error:
            db.session.rollback()
            return {'code': -1, 'msg': str(error)}, 400
        except Exception:
            db.session.rollback()
            raise
    return {'code': 0, 'msg': '关联已保存' if request.method == 'POST' else '获取关联付款单成功', 'data': link_data(invoice)}
