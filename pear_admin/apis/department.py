from flask_jwt_extended import jwt_required
from ._system_validation import validated, payload, required, record, parent_id, selected, nested
from flask import Blueprint, request
from flask_sqlalchemy.pagination import Pagination

from pear_admin.extensions import db
from pear_admin.orms import DepartmentORM

department_api = Blueprint("department", __name__, url_prefix="/department")


@department_api.get("/")
@jwt_required()
def department_list():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("limit", default=10, type=int)

    q = db.select(DepartmentORM)

    pages: Pagination = db.paginate(q, page=max(1, page), per_page=max(1, min(per_page, 200)), error_out=False)

    return {
        "code": 0,
        "msg": "获取部门数据成功",
        "data": [item.json() for item in pages.items],
        "count": pages.total,
    }


@department_api.post("/")
@jwt_required()
@validated
def create_department():
    data = payload()
    data.pop("id", None)
    required(data, "name")
    data["pid"] = parent_id(DepartmentORM, data.get("pid"))
    department = DepartmentORM(**data)
    department.save()
    return {"code": 0, "msg": "新增部门成功"}


@department_api.put("/")
@department_api.put("/<int:rid>")
@jwt_required()
@validated
def change_department(rid=None):
    data = payload()
    rid = rid or data.get("id")
    data.pop("id", None)

    department_obj = record(DepartmentORM, rid)
    if "name" in data:
        required(data, "name")
    if "pid" in data:
        data["pid"] = parent_id(DepartmentORM, data["pid"], rid)
    for key, value in data.items():
        setattr(department_obj, key, value)
    department_obj.save()
    return {"code": 0, "msg": "修改部门成功"}


@department_api.delete("/<int:rid>")
@jwt_required()
@validated
def del_department(rid):
    department_obj = record(DepartmentORM, rid)
    if department_obj.children or department_obj.users:
        raise ValueError("部门下存在子部门或用户，无法删除")
    department_obj.delete()
    return {"code": 0, "msg": "删除部门成功"}


@department_api.get("/treetable")
@jwt_required()
def get_list_as_treetable():
    items = db.session.scalars(db.select(DepartmentORM).order_by(DepartmentORM.id)).all()
    data = nested(items, lambda item: item.json())
    page = max(1, request.args.get("page", 1, type=int))
    limit = max(1, request.args.get("limit", 10, type=int))
    return {"code": 0, "msg": "请求部门数据成功", "data": data[(page-1)*limit:page*limit], "count": len(data)}
