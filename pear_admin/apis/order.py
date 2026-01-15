import json
from datetime import datetime
from decimal import Decimal

from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import cast, String, Date, Numeric

from pear_admin.extensions import db
from pear_admin.orms import OrderORM, SupplierORM, PayORM
from sqlalchemy.orm import selectinload

order_api = Blueprint("order", __name__, url_prefix="/order")


@order_api.get("/")
@jwt_required()
def order_list():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("limit", default=10, type=int)
    
    # 获取搜索参数
    order_id = request.args.get("id", type=int)
    order_number = request.args.get("order_number", type=str)
    material_name = request.args.get("material_name", type=str)
    project_name = request.args.get("project_name", type=str)
    supplier_id = request.args.get("supplier_id", type=int)
    supplier_name = request.args.get("supplier_name", type=str)  # 通过供应商名称筛选
    supplier_contact_person = request.args.get("supplier_contact_person", type=str)  # 通过供应商联系人筛选
    contact_phone = request.args.get("contact_phone", type=str)
    cutting_time = request.args.get("cutting_time", type=str)  # 日期筛选
    estimated_arrival_time = request.args.get("estimated_arrival_time", type=str)  # 日期筛选
    order_amount = request.args.get("order_amount", type=str)
    material_manager = request.args.get("material_manager", type=str)
    sub_project_manager = request.args.get("sub_project_manager", type=str)
    create_at = request.args.get("create_at", type=str)  # 创建时间筛选
    
    # 构建查询
    q = db.select(OrderORM).order_by(OrderORM.id.desc())
    
    # 模糊搜索条件
    if order_id:
        q = q.where(OrderORM.id == order_id)
    if order_number:
        q = q.where(OrderORM.order_number.like(f"%{order_number}%"))
    if material_name:
        q = q.where(OrderORM.material_name.like(f"%{material_name}%"))
    if project_name:
        q = q.where(OrderORM.project_name.like(f"%{project_name}%"))
    if supplier_id:
        q = q.where(OrderORM.supplier_id == supplier_id)
    if supplier_name:
        # 通过供应商名称关联查询（使用子查询避免重复 join）
        supplier_subquery = db.select(SupplierORM.id).where(
            SupplierORM.name.like(f"%{supplier_name}%")
        )
        q = q.where(OrderORM.supplier_id.in_(supplier_subquery))
    if supplier_contact_person:
        # 通过供应商联系人关联查询
        supplier_contact_subquery = db.select(SupplierORM.id).where(
            SupplierORM.contact_person.like(f"%{supplier_contact_person}%")
        )
        q = q.where(OrderORM.supplier_id.in_(supplier_contact_subquery))
    if contact_phone:
        q = q.where(OrderORM.contact_phone.like(f"%{contact_phone}%"))
    if cutting_time:
        # 日期筛选（精确匹配或范围查询）
        try:
            cutting_date = datetime.strptime(cutting_time, "%Y-%m-%d").date()
            q = q.where(OrderORM.cutting_time == cutting_date)
        except ValueError:
            pass
    if estimated_arrival_time:
        try:
            arrival_date = datetime.strptime(estimated_arrival_time, "%Y-%m-%d").date()
            q = q.where(OrderORM.estimated_arrival_time == arrival_date)
        except ValueError:
            pass
    if order_amount:
        # 将金额转为字符串进行模糊搜索
        q = q.where(cast(OrderORM.order_amount, String).like(f"%{order_amount}%"))
    if material_manager:
        q = q.where(OrderORM.material_manager.like(f"%{material_manager}%"))
    if sub_project_manager:
        q = q.where(OrderORM.sub_project_manager.like(f"%{sub_project_manager}%"))
    if create_at:
        # 创建时间筛选（精确匹配日期部分）
        try:
            create_date = datetime.strptime(create_at, "%Y-%m-%d").date()
            q = q.where(db.func.date(OrderORM.create_at) == create_date)
        except ValueError:
            pass
    
    # 使用 selectinload 预加载关联的付款单数据及其供应商关系，避免 N+1 查询
    q = q.options(
        selectinload(OrderORM.pays).selectinload(PayORM.payer),
        selectinload(OrderORM.pays).selectinload(PayORM.payee_supplier)
    )
    
    pages: Pagination = db.paginate(q, page=page, per_page=per_page, error_out=False)
    
    return {
        "code": 0,
        "msg": "获取订单数据成功",
        "data": [item.json() for item in pages.items],
        "count": pages.total,
    }


@order_api.get("/<int:oid>")
@jwt_required()
def get_order(oid):
    # 使用 selectinload 预加载关联的付款单数据
    order_obj = db.session.scalar(
        db.select(OrderORM)
        .options(selectinload(OrderORM.pays))
        .where(OrderORM.id == oid)
    )
    if not order_obj:
        return {"code": -1, "msg": "订单不存在"}
    
    return {
        "code": 0,
        "msg": "获取订单详情成功",
        "data": order_obj.json(),
    }


@order_api.post("/")
@jwt_required()
def create_order():
    try:
        data = request.get_json()
        if not data:
            return {"code": -1, "msg": "请求数据为空"}
        
        if data.get("id"):
            del data["id"]
        
        # 验证必填字段
        if not data.get("order_number"):
            return {"code": -1, "msg": "订单编号不能为空"}
        if not data.get("material_name"):
            return {"code": -1, "msg": "材料名称不能为空"}
        
        # 检查订单编号是否已存在
        existing_order = db.session.scalar(
            db.select(OrderORM).where(OrderORM.order_number == data.get("order_number"))
        )
        if existing_order:
            return {"code": -1, "msg": f"订单编号 {data.get('order_number')} 已存在"}
        
        # 保存附件数据（如果有）
        attachments_data = None
        if "attachments" in data:
            attachments_data = data.pop("attachments")
        
        # 处理日期字段（空字符串转换为 None）
        if data.get("cutting_time"):
            cutting_time_str = str(data["cutting_time"]).strip()
            if cutting_time_str:
                try:
                    data["cutting_time"] = datetime.strptime(cutting_time_str, "%Y-%m-%d").date()
                except ValueError:
                    return {"code": -1, "msg": "下料时间格式错误，应为 YYYY-MM-DD"}
            else:
                data["cutting_time"] = None
        else:
            data["cutting_time"] = None
            
        if data.get("estimated_arrival_time"):
            estimated_arrival_str = str(data["estimated_arrival_time"]).strip()
            if estimated_arrival_str:
                try:
                    data["estimated_arrival_time"] = datetime.strptime(estimated_arrival_str, "%Y-%m-%d").date()
                except ValueError:
                    return {"code": -1, "msg": "预计到场时间格式错误，应为 YYYY-MM-DD"}
            else:
                data["estimated_arrival_time"] = None
        else:
            data["estimated_arrival_time"] = None
        
        # 处理金额字段
        if data.get("order_amount"):
            try:
                data["order_amount"] = Decimal(str(data["order_amount"]))
            except (ValueError, TypeError):
                return {"code": -1, "msg": "订单金额格式错误"}
        
        # 处理供应商ID（确保是整数或None）
        if data.get("supplier_id"):
            try:
                data["supplier_id"] = int(data["supplier_id"])
            except (ValueError, TypeError):
                data["supplier_id"] = None
        
        # 处理附件数据
        if attachments_data:
            data["attachments"] = attachments_data
        
        # 只保留 OrderORM 支持的字段，过滤掉其他字段（如 file 等）
        allowed_fields = {
            'order_number', 'material_name', 'project_name', 'supplier_id',
            'contact_phone', 'cutting_time', 'estimated_arrival_time',
            'material_details', 'order_amount', 'material_manager',
            'sub_project_manager', 'attachments', 'create_at'
        }
        order_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        order = OrderORM(**order_data)
        order.save()
        return {"code": 0, "msg": "新增订单成功", "data": {"id": order.id}}
    except Exception as e:
        db.session.rollback()
        return {"code": -1, "msg": f"新增订单失败: {str(e)}"}


@order_api.put("/<int:oid>")
@order_api.put("/")
@jwt_required()
def change_order(oid=None):
    try:
        data = request.get_json()
        oid = data.get("id") or oid
        
        order_obj = db.session.get(OrderORM, oid)
        if not order_obj:
            return {"code": -1, "msg": "订单不存在"}
        
        # 只处理 OrderORM 支持的字段
        allowed_fields = {
            'order_number', 'material_name', 'project_name', 'supplier_id',
            'contact_phone', 'cutting_time', 'estimated_arrival_time',
            'material_details', 'order_amount', 'material_manager',
            'sub_project_manager', 'attachments', 'create_at'
        }
        
        # 附件数据直接保存为 JSON 字符串
        for key, value in data.items():
            if key == "id" or key not in allowed_fields:
                continue
            if key == "create_at" and value:
                try:
                    value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue
            elif key == "cutting_time":
                if value:
                    cutting_time_str = str(value).strip()
                    if cutting_time_str:
                        try:
                            value = datetime.strptime(cutting_time_str, "%Y-%m-%d").date()
                        except ValueError:
                            continue
                    else:
                        value = None
                else:
                    value = None
            elif key == "estimated_arrival_time":
                if value:
                    estimated_arrival_str = str(value).strip()
                    if estimated_arrival_str:
                        try:
                            value = datetime.strptime(estimated_arrival_str, "%Y-%m-%d").date()
                        except ValueError:
                            continue
                    else:
                        value = None
                else:
                    value = None
            elif key == "order_amount" and value:
                try:
                    value = Decimal(str(value))
                except (ValueError, TypeError):
                    continue
            elif key == "supplier_id" and value:
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    value = None
            elif key == "attachments":
                # 附件数据已经是 JSON 字符串，直接保存
                pass
            setattr(order_obj, key, value)
        
        order_obj.save()
        return {"code": 0, "msg": "修改订单信息成功"}
    except Exception as e:
        db.session.rollback()
        return {"code": -1, "msg": f"修改订单失败: {str(e)}"}


@order_api.delete("/<int:oid>")
@jwt_required()
def del_order(oid):
    order_obj = OrderORM.query.get(oid)
    if not order_obj:
        return {"code": -1, "msg": "订单不存在"}
    
    order_obj.delete()
    return {"code": 0, "msg": "删除订单成功"}

