from datetime import datetime

from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import cast, String

from pear_admin.extensions import db
from pear_admin.orms import SupplierORM

supplier_api = Blueprint("supplier", __name__, url_prefix="/supplier")


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
    
    return {
        "code": 0,
        "msg": "获取供应商数据成功",
        "data": [item.json() for item in pages.items],
        "count": pages.total,
    }


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
    
    for key, value in data.items():
        if key == "id":
            continue
        if key == "create_at" and value:
            value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        setattr(supplier_obj, key, value)
    
    supplier_obj.save()
    return {"code": 0, "msg": "修改供应商信息成功"}


@supplier_api.delete("/<int:sid>")
@jwt_required()
def del_supplier(sid):
    supplier_obj = SupplierORM.query.get(sid)
    if not supplier_obj:
        return {"code": -1, "msg": "供应商不存在"}
    
    supplier_obj.delete()
    return {"code": 0, "msg": "删除供应商成功"}

