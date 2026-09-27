from ._system_validation import validated, payload, required, record, parent_id, selected, nested
from copy import deepcopy

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from pear_admin.extensions import db
from pear_admin.orms import RightsORM

rights_api = Blueprint("rights", __name__, url_prefix="/rights")


@rights_api.get("/")
@jwt_required()
def rights_list():
    return {"code": 0, "msg": "请求权限数据成功，"}


@rights_api.post("/")
@jwt_required()
@validated
def create_rights():
    data = payload()
    data.pop("id", None)
    required(data, "name")
    data["pid"] = parent_id(RightsORM, data.get("pid"))
    if not data.get("sort"):
        data["sort"] = 0
    else:
        data["sort"] = int(data["sort"])
    rights_obj = RightsORM(**data)
    rights_obj.save()
    return {"code": 0, "msg": "新增权限数据成功"}


@rights_api.put("/<int:rid>")
@rights_api.put("/")
@jwt_required()
@validated
def change_rights(rid=None):
    data = payload()
    rid = rid or data.get("id")
    data.pop("id", None)

    rights_obj = record(RightsORM, rid)
    if "name" in data:
        required(data, "name")
    if "pid" in data:
        data["pid"] = parent_id(RightsORM, data["pid"], rid)
    if "sort" in data:
        data["sort"] = int(data["sort"] or 0)
    for key, value in data.items():
        setattr(rights_obj, key, value)
    rights_obj.save()
    return {"code": 0, "msg": "修改权限数据成功"}


@rights_api.delete("/<int:rid>")
@jwt_required()
@validated
def delete_rights(rid):
    rights_obj = record(RightsORM, rid)
    if rights_obj.children:
        raise ValueError("请先删除下级权限")
    rights_obj.delete()
    return {"code": 0, "msg": "删除权限数据成功"}


@rights_api.get("/tree")
def get_list_as_tree():
    items = db.session.scalars(db.select(RightsORM).order_by(RightsORM.sort, RightsORM.id)).all()
    data = nested(items, lambda item: {"id": item.id, "pid": item.pid, "title": item.name, "sort": item.sort})
    return {"code": 0, "data": data}


@rights_api.get("/treetable")
def get_list_as_treetable():
    items = db.session.scalars(db.select(RightsORM).order_by(RightsORM.sort, RightsORM.id)).all()
    data = nested(items, lambda item: item.json())
    page = max(1, request.args.get("page", 1, type=int))
    limit = max(1, request.args.get("limit", request.args.get("per_page", 10, type=int), type=int))
    return {"code": 0, "msg": "请求权限数据成功", "data": data[(page-1)*limit:page*limit], "count": len(data)}
