"""
Dashboard API - 数据看板接口
"""
from flask import Blueprint
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from datetime import datetime, timedelta

from pear_admin.extensions import db
from pear_admin.orms import OrderORM, PayORM, SupplierORM, PayerORM

dashboard_api = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_api.get("/overview")
@jwt_required()
def get_overview():
    """获取财务概览数据"""
    
    # 订单总金额
    total_order_amount = db.session.execute(
        db.select(func.sum(OrderORM.order_amount))
    ).scalar() or 0
    
    # 已付款总额
    total_paid_amount = db.session.execute(
        db.select(func.sum(PayORM.current_payment_amount))
    ).scalar() or 0
    
    # 待付款余额
    pending_amount = float(total_order_amount) - float(total_paid_amount)
    
    # 订单数量
    order_count = db.session.execute(
        db.select(func.count(OrderORM.id))
    ).scalar() or 0
    
    # 付款单数量
    pay_count = db.session.execute(
        db.select(func.count(PayORM.id))
    ).scalar() or 0
    
    # 供应商数量
    supplier_count = db.session.execute(
        db.select(func.count(SupplierORM.id))
    ).scalar() or 0
    
    # 付款单位数量
    payer_count = db.session.execute(
        db.select(func.count(PayerORM.id))
    ).scalar() or 0
    
    return {
        "code": 0,
        "msg": "获取成功",
        "data": {
            "total_order_amount": round(float(total_order_amount), 2),
            "total_paid_amount": round(float(total_paid_amount), 2),
            "pending_amount": round(pending_amount, 2),
            "order_count": order_count,
            "pay_count": pay_count,
            "supplier_count": supplier_count,
            "payer_count": payer_count
        }
    }


@dashboard_api.get("/payment-status")
@jwt_required()
def get_payment_status():
    """获取付款状态分布"""
    
    # 按付款状态分组统计
    result = db.session.execute(
        db.select(
            PayORM.payment_status,
            func.count(PayORM.id).label("count"),
            func.sum(PayORM.current_payment_amount).label("amount")
        ).group_by(PayORM.payment_status)
    ).all()
    
    status_distribution = []
    for row in result:
        status = row.payment_status or "未设置"
        count = row.count or 0
        amount = float(row.amount) if row.amount else 0
        status_distribution.append({
            "status": status,
            "count": count,
            "amount": round(amount, 2)
        })
    
    return {
        "code": 0,
        "msg": "获取成功",
        "data": {
            "status_distribution": status_distribution
        }
    }


@dashboard_api.get("/monthly-trend")
@jwt_required()
def get_monthly_trend():
    """获取月度趋势数据（最近12个月）"""
    
    # 计算最近12个月的范围
    today = datetime.now()
    start_date = datetime(today.year - 1, today.month, 1)
    
    # 判断数据库类型
    bind = db.session.get_bind()
    is_mysql = "mysql" in bind.dialect.name
    
    if is_mysql:
        # MySQL: 使用 date_format
        date_func = func.date_format(OrderORM.create_at, '%Y-%m')
        pay_date_func = func.date_format(PayORM.create_at, '%Y-%m')
    else:
        # SQLite: 使用 strftime
        date_func = func.strftime('%Y-%m', OrderORM.create_at)
        pay_date_func = func.strftime('%Y-%m', PayORM.create_at)

    # 订单月度趋势
    order_trend = db.session.execute(
        db.select(
            date_func.label("month"),
            func.count(OrderORM.id).label("count"),
            func.sum(OrderORM.order_amount).label("amount")
        ).where(OrderORM.create_at >= start_date)
        .group_by(date_func)
        .order_by(date_func)
    ).all()
    
    # 付款月度趋势
    pay_trend = db.session.execute(
        db.select(
            pay_date_func.label("month"),
            func.count(PayORM.id).label("count"),
            func.sum(PayORM.current_payment_amount).label("amount")
        ).where(PayORM.create_at >= start_date)
        .group_by(pay_date_func)
        .order_by(pay_date_func)
    ).all()
    
    order_data = []
    for row in order_trend:
        order_data.append({
            "month": row.month,
            "count": row.count or 0,
            "amount": round(float(row.amount), 2) if row.amount else 0
        })
    
    pay_data = []
    for row in pay_trend:
        pay_data.append({
            "month": row.month,
            "count": row.count or 0,
            "amount": round(float(row.amount), 2) if row.amount else 0
        })
    
    return {
        "code": 0,
        "msg": "获取成功",
        "data": {
            "order_trend": order_data,
            "pay_trend": pay_data
        }
    }


@dashboard_api.get("/top-suppliers")
@jwt_required()
def get_top_suppliers():
    """获取TOP10供应商（按订单金额）"""
    
    result = db.session.execute(
        db.select(
            SupplierORM.id,
            SupplierORM.name,
            func.count(OrderORM.id).label("order_count"),
            func.sum(OrderORM.order_amount).label("total_amount")
        ).join(OrderORM, OrderORM.supplier_id == SupplierORM.id)
        .group_by(SupplierORM.id, SupplierORM.name)
        .order_by(func.sum(OrderORM.order_amount).desc())
        .limit(10)
    ).all()
    
    suppliers = []
    for row in result:
        suppliers.append({
            "id": row.id,
            "name": row.name,
            "order_count": row.order_count or 0,
            "total_amount": round(float(row.total_amount), 2) if row.total_amount else 0
        })
    
    return {
        "code": 0,
        "msg": "获取成功",
        "data": {
            "top_suppliers": suppliers
        }
    }
