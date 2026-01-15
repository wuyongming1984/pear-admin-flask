from datetime import datetime

from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import cast, String

from pear_admin.extensions import db
from pear_admin.orms import PayerORM

payer_api = Blueprint("payer", __name__, url_prefix="/payer")


@payer_api.get("/")
@jwt_required()
def payer_list():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("limit", default=10, type=int)
    
    # 获取搜索参数
    type_id = request.args.get("type_id", type=int)
    name = request.args.get("name", type=str)
    bank_name = request.args.get("bank_name", type=str)
    account_number = request.args.get("account_number", type=str)
    remark = request.args.get("remark", type=str)
    
    # 构建查询
    q = db.select(PayerORM)
    
    # 模糊搜索条件
    if type_id:
        q = q.where(PayerORM.type_id == type_id)
    if name:
        q = q.where(PayerORM.name.like(f"%{name}%"))
    if bank_name:
        q = q.where(PayerORM.bank_name.like(f"%{bank_name}%"))
    if account_number:
        # 将账号转为字符串进行搜索
        q = q.where(cast(PayerORM.account_number, String).like(f"%{account_number}%"))
    if remark:
        q = q.where(PayerORM.remark.like(f"%{remark}%"))
    
    pages: Pagination = db.paginate(q, page=page, per_page=per_page, error_out=False)
    
    return {
        "code": 0,
        "msg": "获取付款单位数据成功",
        "data": [item.json() for item in pages.items],
        "count": pages.total,
    }


@payer_api.post("/")
@jwt_required()
def create_payer():
    data = request.get_json()
    if data.get("id"):
        del data["id"]
    
    payer = PayerORM(**data)
    payer.save()
    return {"code": 0, "msg": "新增付款单位成功"}


@payer_api.put("/<int:pid>")
@payer_api.put("/")
@jwt_required()
def change_payer(pid=None):
    data = request.get_json()
    pid = data.get("id") or pid
    
    payer_obj = PayerORM.query.get(pid)
    if not payer_obj:
        return {"code": -1, "msg": "付款单位不存在"}
    
    for key, value in data.items():
        if key == "id":
            continue
        if key == "create_at" and value:
            # 尝试解析时间，如果格式不对则跳过或报错
            try:
                if isinstance(value, str):
                    value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass # 或者做其他处理
        setattr(payer_obj, key, value)
    
    payer_obj.save()
    return {"code": 0, "msg": "修改付款单位信息成功"}


@payer_api.delete("/<int:pid>")
@jwt_required()
def del_payer(pid):
    payer_obj = PayerORM.query.get(pid)
    if not payer_obj:
        return {"code": -1, "msg": "付款单位不存在"}
    
    payer_obj.delete()
    return {"code": 0, "msg": "删除付款单位成功"}
