"""Append invoice/payment links without replacing other linked invoices."""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from sqlalchemy.orm import load_only, selectinload

from pear_admin.extensions import db
from pear_admin.orms import MaterialInvoiceORM, PayORM, SupplierORM, OrderORM
from pear_admin.invoice_links import same_company, selected_ids
from pear_admin.invoice_recommendations import invoice_payment_recommendations, payment_recommendations

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
    return invoice_payment_recommendations(invoice)


@invoice_links_api.post('/payments/recommendations')
@jwt_required()
def recommend_payment_invoices():
    try:
        data = payment_recommendations(request.get_json(silent=True))
    except ValueError as error:
        return {'code': -1, 'msg': str(error)}, 400
    return {'code': 0, 'msg': '获取智能关联建议成功', 'data': data}


@invoice_links_api.route('/invoices/<int:invoice_id>/payments', methods=['GET', 'POST'])
@jwt_required()
def invoice_payments(invoice_id):
    query = db.select(MaterialInvoiceORM).where(MaterialInvoiceORM.id == invoice_id).options(load_only(
        MaterialInvoiceORM.id, MaterialInvoiceORM.seller_name, MaterialInvoiceORM.buyer_name,
        MaterialInvoiceORM.invoice_date, MaterialInvoiceORM.total_amount, MaterialInvoiceORM.tax_amount,
        MaterialInvoiceORM.project_id, MaterialInvoiceORM.invoice_type, MaterialInvoiceORM.invoice_name))
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
