from datetime import datetime
from decimal import Decimal

from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from flask_sqlalchemy.pagination import Pagination

from pear_admin.extensions import db
from pear_admin.orms import PayORM, OrderORM, SupplierORM

pay_api = Blueprint("pay", __name__, url_prefix="/pay")


@pay_api.get("/")
@jwt_required()
def pay_list():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("limit", default=10, type=int)
    
    # 获取搜索参数
    pay_id = request.args.get("id", type=int)
    pay_number = request.args.get("pay_number", type=str)
    order_id = request.args.get("order_id", type=int)
    order_number = request.args.get("order_number", type=str)
    payer_supplier_id = request.args.get("payer_supplier_id", type=int)
    payer_supplier_name = request.args.get("payer_supplier_name", type=str)
    payee_supplier_id = request.args.get("payee_supplier_id", type=int)
    payee_supplier_name = request.args.get("payee_supplier_name", type=str)
    payment_status = request.args.get("payment_status", type=str)
    handler = request.args.get("handler", type=str)
    create_at = request.args.get("create_at", type=str)
    
    # 构建查询
    q = db.select(PayORM)
    
    # 模糊搜索条件
    if pay_id:
        q = q.where(PayORM.id == pay_id)
    if pay_number:
        q = q.where(PayORM.pay_number.like(f"%{pay_number}%"))
    if order_id:
        q = q.where(PayORM.order_id == order_id)
    if order_number:
        # 通过订单编号筛选（需要关联订单表）
        subquery = db.select(OrderORM.id).filter(OrderORM.order_number.like(f"%{order_number}%")).scalar_subquery()
        q = q.where(PayORM.order_id.in_(subquery))
    if payer_supplier_id:
        q = q.where(PayORM.payer_supplier_id == payer_supplier_id)
    if payer_supplier_name:
        # 通过付款单位名称筛选
        subquery = db.select(SupplierORM.id).filter(SupplierORM.name.like(f"%{payer_supplier_name}%")).scalar_subquery()
        q = q.where(PayORM.payer_supplier_id.in_(subquery))
    if payee_supplier_id:
        q = q.where(PayORM.payee_supplier_id == payee_supplier_id)
    if payee_supplier_name:
        # 通过收款单位名称筛选
        subquery = db.select(SupplierORM.id).filter(SupplierORM.name.like(f"%{payee_supplier_name}%")).scalar_subquery()
        q = q.where(PayORM.payee_supplier_id.in_(subquery))
    if payment_status:
        q = q.where(PayORM.payment_status.like(f"%{payment_status}%"))
    if handler:
        q = q.where(PayORM.handler.like(f"%{handler}%"))
    if create_at:
        # 创建时间筛选（精确匹配日期部分）
        try:
            create_date = datetime.strptime(create_at, "%Y-%m-%d").date()
            q = q.where(db.func.date(PayORM.create_at) == create_date)
        except ValueError:
            pass
    
    pages: Pagination = db.paginate(q, page=page, per_page=per_page, error_out=False)
    
    return {
        "code": 0,
        "msg": "获取付款单数据成功",
        "data": [item.json() for item in pages.items],
        "count": pages.total,
    }


@pay_api.get("/<int:pid>")
@jwt_required()
def get_pay(pid):
    pay_obj = db.session.get(PayORM, pid)
    if not pay_obj:
        return {"code": -1, "msg": "付款单不存在"}
    
    return {
        "code": 0,
        "msg": "获取付款单数据成功",
        "data": pay_obj.json(),
    }


@pay_api.post("/")
@jwt_required()
def create_pay():
    data = request.get_json()
    if data.get("id"):
        del data["id"]
    
    # 处理金额字段
    if data.get("current_payment_amount"):
        data["current_payment_amount"] = Decimal(str(data["current_payment_amount"]))
    if data.get("invoice_amount"):
        data["invoice_amount"] = Decimal(str(data["invoice_amount"]))
    
    # 处理日期字段（如果有）
    if data.get("create_at") and isinstance(data["create_at"], str):
        try:
            data["create_at"] = datetime.strptime(data["create_at"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    
    pay = PayORM(**data)
    pay.save()
    return {"code": 0, "msg": "新增付款单成功"}


@pay_api.put("/<int:pid>")
@pay_api.put("/")
@jwt_required()
def change_pay(pid=None):
    data = request.get_json()
    pid = data.get("id") or pid
    
    pay_obj = db.session.get(PayORM, pid)
    if not pay_obj:
        return {"code": -1, "msg": "付款单不存在"}
    
    # 更新字段
    for key, value in data.items():
        if key == "id":
            continue
        if key == "create_at" and value:
            try:
                value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
        elif key == "current_payment_amount" and value:
            value = Decimal(str(value))
        elif key == "invoice_amount" and value:
            value = Decimal(str(value))
        setattr(pay_obj, key, value)
    
    pay_obj.save()
    return {"code": 0, "msg": "修改付款单信息成功"}


@pay_api.delete("/<int:pid>")
@jwt_required()
def del_pay(pid):
    pay_obj = db.session.get(PayORM, pid)
    if not pay_obj:
        return {"code": -1, "msg": "付款单不存在"}
    
    pay_obj.delete()
    return {"code": 0, "msg": "删除付款单成功"}
