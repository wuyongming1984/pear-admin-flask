from datetime import datetime
import secrets

from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import cast, String

from pear_admin.extensions import db
from pear_admin.orms import SupplierORM

supplier_api = Blueprint("supplier", __name__, url_prefix="/supplier")


@supplier_api.post("/<int:sid>/token")
@jwt_required()
def generate_supplier_token(sid):
    """生成或重置供应商访问令牌"""
    supplier = SupplierORM.query.get(sid)
    if not supplier:
        return {"code": -1, "msg": "供应商不存在"}
    
    # Generate secure token
    token = secrets.token_urlsafe(32)
    supplier.access_token = token
    supplier.save()
    
    return {
        "code": 0, 
        "msg": "令牌生成成功", 
        "data": {
            "token": token,
            "url": f"/portal/reconcile/{token}"
        }
    }


@supplier_api.get("/")
@jwt_required()
def supplier_list():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("limit", default=10, type=int)
    
    # 获取搜索参数
    type_id = request.args.get("type_id", type=int)
    name = request.args.get("name", type=str)
    contact_person = request.args.get("contact_person", type=str)
    phone = request.args.get("phone", type=str)
    email = request.args.get("email", type=str)
    bank_name = request.args.get("bank_name", type=str)
    account_number = request.args.get("account_number", type=str)
    address = request.args.get("address", type=str)
    remark = request.args.get("remark", type=str)
    
    # 构建查询
    q = db.select(SupplierORM)
    
    # 模糊搜索条件
    if type_id:
        q = q.where(SupplierORM.type_id == type_id)
    if name:
        q = q.where(SupplierORM.name.like(f"%{name}%"))
    if contact_person:
        q = q.where(SupplierORM.contact_person.like(f"%{contact_person}%"))
    if phone:
        q = q.where(SupplierORM.phone.like(f"%{phone}%"))
    if email:
        q = q.where(SupplierORM.email.like(f"%{email}%"))
    if bank_name:
        q = q.where(SupplierORM.bank_name.like(f"%{bank_name}%"))
    if account_number:
        # 将账号转为字符串进行搜索
        q = q.where(cast(SupplierORM.account_number, String).like(f"%{account_number}%"))
    if address:
        q = q.where(SupplierORM.address.like(f"%{address}%"))
    if remark:
        q = q.where(SupplierORM.remark.like(f"%{remark}%"))
    
    pages: Pagination = db.paginate(q, page=page, per_page=per_page, error_out=False)
    
    mode = request.args.get("mode", type=str)
    if mode == "slim":
        data_list = [item.slim_json() for item in pages.items]
    else:
        data_list = [item.json() for item in pages.items]

    return {
        "code": 0,
        "msg": "获取供应商数据成功",
        "data": data_list,
        "count": pages.total,
    }


@supplier_api.get("/<int:sid>")
@jwt_required()
def get_supplier(sid):
    supplier = SupplierORM.query.get(sid)
    if not supplier:
        return {"code": -1, "msg": "供应商不存在"}
    return {"code": 0, "msg": "获取供应商成功", "data": supplier.json()}


@supplier_api.post("/")
@jwt_required()
def create_supplier():
    data = request.get_json()
    if data.get("id"):
        del data["id"]
    
    supplier = SupplierORM(**data)
    supplier.save()
    return {"code": 0, "msg": "新增供应商成功"}


@supplier_api.put("/<int:sid>")
@supplier_api.put("/")
@jwt_required()
def change_supplier(sid=None):
    data = request.get_json()
    sid = data.get("id") or sid
    
    supplier_obj = SupplierORM.query.get(sid)
    if not supplier_obj:
        return {"code": -1, "msg": "供应商不存在"}
    
    # 检测联系人是否变更
    old_contact_person = supplier_obj.contact_person
    new_contact_person = data.get("contact_person")
    
    print(f"[DEBUG] 旧联系人: {old_contact_person}, 新联系人: {new_contact_person}")  # 调试日志
    
    if new_contact_person and new_contact_person != old_contact_person:
        # 查询所有使用旧联系人的订单
        from pear_admin.orms import OrderORM
        related_orders = OrderORM.query.filter_by(
            supplier_contact_person=old_contact_person
        ).all()
        
        print(f"[DEBUG] 找到 {len(related_orders)} 个关联订单")  # 调试日志
        
        if related_orders:
            # 返回需要确认的订单列表
            order_list = []
            for order in related_orders:
                order_list.append({
                    "id": order.id,
                    "order_number": order.order_number,
                    "material_name": order.material_name,
                    "order_amount": float(order.order_amount) if order.order_amount else 0,
                    "project_name": order.project.project_name if order.project else "未关联项目"
                })
            
            response_data = {
                "code": 1001,
                "msg": f"检测到 {len(related_orders)} 个订单使用联系人 '{old_contact_person}'，需要确认是否同步更新",
                "data": {
                    "old_contact_person": old_contact_person,
                    "new_contact_person": new_contact_person,
                    "related_orders": order_list
                }
            }
            print(f"[DEBUG] 返回响应: {response_data}")  # 调试日志
            return response_data
    
    # 没有联系人变更或没有关联订单，直接更新
    for key, value in data.items():
        if key == "id":
            continue
        if key == "create_at" and value:
            value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        setattr(supplier_obj, key, value)
    
    supplier_obj.save()
    return {"code": 0, "msg": "修改供应商信息成功"}



@supplier_api.post("/<int:sid>/update-with-orders")
@jwt_required()
def update_supplier_with_orders(sid):
    """批量更新供应商和关联订单的联系人"""
    data = request.get_json()
    supplier_data = data.get("supplier_data")
    confirmed_order_ids = data.get("confirmed_order_ids", [])
    
    if not supplier_data:
        return {"code": -1, "msg": "缺少供应商数据"}
    
    supplier_obj = SupplierORM.query.get(sid)
    if not supplier_obj:
        return {"code": -1, "msg": "供应商不存在"}
    
    # 获取旧联系人
    old_contact_person = supplier_obj.contact_person
    new_contact_person = supplier_data.get("contact_person")
    
    if not new_contact_person or new_contact_person == old_contact_person:
        return {"code": -1, "msg": "联系人未变更"}
    
    # 查询所有使用旧联系人的订单
    from pear_admin.orms import OrderORM
    related_orders = OrderORM.query.filter_by(
        supplier_contact_person=old_contact_person
    ).all()
    
    # 验证确认的订单ID列表是否完整
    related_order_ids = {order.id for order in related_orders}
    confirmed_order_ids_set = set(confirmed_order_ids)
    
    if related_order_ids != confirmed_order_ids_set:
        missing_ids = related_order_ids - confirmed_order_ids_set
        return {
            "code": -1, 
            "msg": f"必须确认所有关联订单才能修改。缺少订单ID: {list(missing_ids)}"
        }
    
    # 开始事务性更新
    try:
        # 更新供应商信息
        for key, value in supplier_data.items():
            if key == "id":
                continue
            if key == "create_at" and value:
                value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            setattr(supplier_obj, key, value)
        
        # 批量更新订单的联系人
        for order in related_orders:
            order.supplier_contact_person = new_contact_person
        
        db.session.commit()
        
        result = {
            "code": 0, 
            "msg": f"成功更新供应商和 {len(related_orders)} 个订单的联系人"
        }
        print(f"[DEBUG] 批量更新成功，返回: {result}")  # 调试日志
        return result
    except Exception as e:
        db.session.rollback()
        error_result = {"code": -1, "msg": f"更新失败: {str(e)}"}
        print(f"[DEBUG] 批量更新失败，返回: {error_result}")  # 调试日志
        return error_result


@supplier_api.delete("/<int:sid>")
@jwt_required()
def del_supplier(sid):
    supplier_obj = SupplierORM.query.get(sid)
    if not supplier_obj:
        return {"code": -1, "msg": "供应商不存在"}
    
    supplier_obj.delete()
    return {"code": 0, "msg": "删除供应商成功"}
