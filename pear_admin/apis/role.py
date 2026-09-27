from flask_jwt_extended import jwt_required
from ._system_validation import validated, payload, required, record, parent_id, selected, nested
from flask import Blueprint, request
from flask_sqlalchemy.pagination import Pagination

from pear_admin.extensions import db
from pear_admin.orms import RightsORM, RoleORM

role_api = Blueprint("role", __name__, url_prefix="/role")


@role_api.get("/")
@jwt_required()
def role_list():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("limit", default=10, type=int)
    q = db.select(RoleORM)

    if request.args.get("type") == "tree":
        items = db.session.scalars(q.order_by(RoleORM.id)).all()
        return {"code": 0, "data": [item.json() for item in items], "count": len(items)}
    pages: Pagination = db.paginate(q, page=max(1, page), per_page=max(1, min(per_page, 200)), error_out=False)

    return {
        "code": 0,
        "msg": "获取角色数据成功",
        "data": [item.json() for item in pages.items],
        "count": pages.total,
    }


@role_api.post("/")
@jwt_required()
@validated
def create_role():
    data = payload()
    data.pop("id", None)
    required(data, "name", "code")
    role = RoleORM(**data)
    role.save()
    return {"code": 0, "msg": "新增角色成功"}


@role_api.put("/<int:rid>")
@role_api.put("/")
@jwt_required()
@validated
def change_role(rid=None):
    data = payload()
    rid = rid or data.get("id")
    data.pop("id", None)

    role_obj = record(RoleORM, rid)
    for key in ("name", "code"):
        if key in data:
            required(data, key)
    for key, value in data.items():
        setattr(role_obj, key, value)
    role_obj.save()
    return {"code": 0, "msg": "修改角色权限成功"}


@role_api.delete("/<int:rid>")
@jwt_required()
@validated
def del_role(rid):
    role_obj = record(RoleORM, rid)
    role_obj.delete()
    return {"code": 0, "msg": "删除角色成功"}


@role_api.get("/role_rights/<int:rid>")
@jwt_required()
@validated
def role_rights(rid):
    role: RoleORM = db.session.execute(
        db.select(RoleORM).where(RoleORM.id == rid)
    ).scalar()
    if role is None:
        raise ValueError("角色不存在")
    own_rights_list = [r.id for r in role.rights_list]

    return {
        "code": 0,
        "msg": "返回角色权限数据成功",
        "data": own_rights_list,
    }


@role_api.put("/role_rights/<int:rid>")
@jwt_required()
@validated
def change_role_rights(rid):
    role = record(RoleORM, rid)
    role.rights_list = selected(RightsORM, payload().get("rights_ids", ""))
    role.rights_ids = ",".join(str(item.id) for item in role.rights_list)
    role.save()
    return {"code": 0, "msg": "授权成功"}
