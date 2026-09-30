"""Paged document cards; filter metadata and totals never serialize history."""
from decimal import Decimal

from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from pear_admin.extensions import db
from pear_admin.orms import OrderORM, PayORM, ProjectORM

document_workspace_api = Blueprint('document_workspace', __name__, url_prefix='/workspace')


def _project_filters():
    project_id = request.args.get('project_id', type=int)
    project_name = request.args.get('project_name', '').strip()
    if project_id is not None:
        return [OrderORM.project_id == project_id]
    if project_name:
        return [OrderORM.project_id.in_(db.select(ProjectORM.id).where(ProjectORM.project_name == project_name))]
    return []


def _contains(column, key):
    value = request.args.get(key, '').strip()
    return [func.lower(column).contains(value.lower(), autoescape=True)] if value else []


def _paid_totals():
    return (db.select(PayORM.order_id, func.sum(PayORM.current_payment_amount).label('paid'))
            .group_by(PayORM.order_id).subquery())


def _money(value):
    return format(Decimal(value or 0), '.2f')


def _metadata(payment=False):
    # Each sidebar follows the OTHER selection, so alternatives remain selectable.
    project_query = db.select(ProjectORM.id, ProjectORM.project_name).order_by(ProjectORM.id)
    contact = request.args.get('supplier_contact_person', '')
    if contact:
        matching_projects = db.select(OrderORM.project_id).where(OrderORM.supplier_contact_person == contact)
        if payment:
            matching_projects = matching_projects.join(PayORM, PayORM.order_id == OrderORM.id)
        project_query = project_query.where(ProjectORM.id.in_(matching_projects))
    projects = [dict(id=p.id, project_name=p.project_name) for p in db.session.execute(project_query)]
    contacts = db.select(OrderORM.supplier_contact_person).where(*_project_filters())
    if payment:
        contacts = contacts.join(PayORM, PayORM.order_id == OrderORM.id)
    contacts = contacts.where(OrderORM.supplier_contact_person.isnot(None),
                              OrderORM.supplier_contact_person != '').distinct()
    return projects, list(db.session.scalars(contacts))


def _pagination(query):
    page = max(1, request.args.get('page', 1, type=int))
    limit = max(1, min(100, request.args.get('limit', 20, type=int)))
    return db.paginate(query, page=page, per_page=limit, error_out=False)


@document_workspace_api.get('/orders')
@jwt_required()
def orders():
    paid = _paid_totals()
    paid_amount = func.coalesce(paid.c.paid, 0)
    amount = func.coalesce(OrderORM.order_amount, 0)
    filters = _project_filters() + _contains(OrderORM.order_number, 'order_number')
    contact = request.args.get('supplier_contact_person', '')
    if contact:
        filters.append(OrderORM.supplier_contact_person == contact)
    summary = db.session.execute(db.select(func.sum(amount), func.sum(paid_amount))
        .select_from(OrderORM).outerjoin(paid, paid.c.order_id == OrderORM.id).where(*filters)).one()
    query = db.select(OrderORM).where(*filters)
    if request.args.get('hide_settled') == '1':
        query = query.outerjoin(paid, paid.c.order_id == OrderORM.id).where(func.abs(amount - paid_amount) > Decimal('0.01'))
    query = query.order_by(OrderORM.id.desc()).options(
        selectinload(OrderORM.project), selectinload(OrderORM.supplier),
        selectinload(OrderORM.pays).selectinload(PayORM.payer),
        selectinload(OrderORM.pays).selectinload(PayORM.payee_supplier))
    pages = _pagination(query)
    data = []
    for order in pages.items:
        row = order.json()
        # Keep financial arithmetic exact, including split payments and refunds.
        paid_value = sum((p.current_payment_amount or Decimal(0) for p in order.pays), Decimal(0))
        row.update(paid_amount=_money(paid_value), order_balance=_money((order.order_amount or 0) - paid_value))
        data.append(row)
    projects, contacts = _metadata()
    return dict(code=0, data=data, count=pages.total, projects=projects, contacts=contacts,
                totals=dict(orders=_money(summary[0]), paid=_money(summary[1]),
                            balance=_money((summary[0] or 0) - (summary[1] or 0))))


@document_workspace_api.get('/payments')
@jwt_required()
def payments():
    filters = _project_filters() + _contains(PayORM.pay_number, 'pay_number') + _contains(OrderORM.order_number, 'order_number')
    contact = request.args.get('supplier_contact_person', '')
    status = request.args.get('payment_status', '')
    if contact:
        filters.append(OrderORM.supplier_contact_person == contact)
    if status:
        filters.append(PayORM.payment_status == status)
    summary = db.session.execute(db.select(func.sum(PayORM.current_payment_amount), func.sum(PayORM.invoice_amount))
        .select_from(PayORM).outerjoin(OrderORM, OrderORM.id == PayORM.order_id).where(*filters)).one()
    query = (db.select(PayORM).outerjoin(OrderORM, OrderORM.id == PayORM.order_id).where(*filters)
             .order_by(PayORM.id.desc()).options(
                 selectinload(PayORM.order).selectinload(OrderORM.project),
                 selectinload(PayORM.payer), selectinload(PayORM.payee_supplier), selectinload(PayORM.invoices)))
    pages = _pagination(query)
    order_ids = {p.order_id for p in pages.items if p.order_id is not None}
    paid = dict(db.session.execute(db.select(PayORM.order_id, func.sum(PayORM.current_payment_amount))
                .where(PayORM.order_id.in_(order_ids)).group_by(PayORM.order_id)).all()) if order_ids else {}
    data = []
    for payment in pages.items:
        row = payment.json()
        order, supplier = payment.order, payment.payee_supplier
        row['order_summary'] = dict(
            id=order.id, order_number=order.order_number, project_id=order.project_id,
            project_name=order.project.project_name if order.project else None,
            supplier_contact_person=order.supplier_contact_person, material_name=order.material_name,
            order_amount=_money(order.order_amount), paid_amount=_money(paid.get(order.id)),
            order_balance=_money((order.order_amount or 0) - (paid.get(order.id) or 0))) if order else {}
        row['payee_account'] = dict(bank_name=supplier.bank_name, account_number=supplier.account_number) if supplier else {}
        data.append(row)
    projects, contacts = _metadata(payment=True)
    return dict(code=0, data=data, count=pages.total, projects=projects, contacts=contacts,
                totals=dict(paid=_money(summary[0]), invoiced=_money(summary[1])))
