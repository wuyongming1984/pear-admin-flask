from datetime import datetime
from decimal import Decimal

from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from flask_sqlalchemy.pagination import Pagination

from pear_admin.extensions import db
from pear_admin.orms import PayORM, OrderORM, SupplierORM, PayerORM

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
    project_name = request.args.get("project_name", type=str)
    supplier_contact_person = request.args.get("supplier_contact_person", type=str)
    create_at = request.args.get("create_at", type=str)
    
    # 构建查询（按ID倒序，新的在前）
    q = db.select(PayORM).order_by(PayORM.id.desc())
    
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
        # 通过付款单位名称筛选 (使用 PayerORM)
        subquery = db.select(PayerORM.id).filter(PayerORM.name.like(f"%{payer_supplier_name}%")).scalar_subquery()
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
    if project_name:
        # 通过关联订单的项目名称筛选
        from pear_admin.orms import ProjectORM
        subquery = db.select(OrderORM.id).join(ProjectORM).where(
            ProjectORM.project_name.like(f"%{project_name}%")
        ).scalar_subquery()
        q = q.where(PayORM.order_id.in_(subquery))
    if supplier_contact_person:
        # 通过关联订单的供应商联系人筛选
        subquery = db.select(OrderORM.id).where(
            OrderORM.supplier_contact_person.like(f"%{supplier_contact_person}%")
        ).scalar_subquery()
        q = q.where(PayORM.order_id.in_(subquery))
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
    from pear_admin.orms.material import MaterialInvoiceORM
    
    data = request.get_json()
    if data.get("id"):
        del data["id"]
    
    # 提取发票ID列表
    invoice_ids = data.pop("invoice_ids", [])
    
    # 定义允许的字段 (白名单)
    valid_fields = [
        "pay_number", "order_id", "payer_supplier_id", "payee_supplier_id",
        "payment_purpose", "current_payment_amount", "invoice_amount",
        "payment_status", "handler", "create_at", "attachments"
    ]
    
    clean_data = {}
    
    # 过滤和转换数据
    for key, value in data.items():
        if key not in valid_fields:
            continue
            
        # 跳过空值，使用数据库默认值或NULL
        if value == "" or value is None:
            clean_data[key] = None
            continue
            
        if key in ["current_payment_amount", "invoice_amount"]:
            try:
                clean_data[key] = Decimal(str(value))
            except Exception:
                return {"code": -1, "msg": f"{key} 格式错误，必须为数字"}
        elif key in ["order_id", "payer_supplier_id", "payee_supplier_id"]:
            try:
                clean_data[key] = int(value)
            except ValueError:
                return {"code": -1, "msg": f"{key} 格式错误，必须为整数"}
        elif key == "create_at":
             try:
                clean_data[key] = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
             except ValueError:
                 # 如果格式不对，或者不需要转换(已经是datetime)，则忽略或保留原值
                 # 这里假设前端传字符串，如果传错，让数据库报错或忽略
                 pass
        else:
            clean_data[key] = value

    try:
        pay = PayORM(**clean_data)
        db.session.add(pay)
        db.session.flush()  # 获取pay的ID
        
        # 关联发票
        if invoice_ids and isinstance(invoice_ids, list):
            for invoice_id in invoice_ids:
                invoice = db.session.get(MaterialInvoiceORM, int(invoice_id))
                if invoice:
                    pay.invoices.append(invoice)
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # 记录具体错误
        print(f"Create Pay Error: {e}") 
        return {"code": -1, "msg": f"新增付款单失败: {str(e)}"}
        
    return {"code": 0, "msg": "新增付款单成功"}


@pay_api.put("/<int:pid>")
@pay_api.put("/")
@jwt_required()
def change_pay(pid=None):
    from pear_admin.orms.material import MaterialInvoiceORM
    
    data = request.get_json()
    pid = data.get("id") or pid
    
    pay_obj = db.session.get(PayORM, pid)
    if not pay_obj:
        return {"code": -1, "msg": "付款单不存在"}
    
    # 提取发票ID列表
    invoice_ids = data.pop("invoice_ids", None)
    
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
        elif key == "attachments":
            # attachments 是 JSON 字符串,直接保存
            pass
        setattr(pay_obj, key, value)
    
    # 更新发票关联
    if invoice_ids is not None:
        # 清除现有关联
        pay_obj.invoices.clear()
        # 添加新关联
        if isinstance(invoice_ids, list):
            for invoice_id in invoice_ids:
                invoice = db.session.get(MaterialInvoiceORM, int(invoice_id))
                if invoice:
                    pay_obj.invoices.append(invoice)
    
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
