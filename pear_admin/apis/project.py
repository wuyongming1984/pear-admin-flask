from datetime import datetime
from decimal import Decimal

import json

from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import cast, String, or_
from sqlalchemy.orm import load_only, selectinload

from pear_admin.extensions import db
from pear_admin.orms import AttachmentORM, ProjectORM

project_api = Blueprint("project", __name__, url_prefix="/project")


@project_api.get("/")
@jwt_required()
def project_list():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("limit", default=10, type=int)
    
    # 获取搜索参数
    project_name = request.args.get("project_name", type=str)
    project_full_name = request.args.get("project_full_name", type=str)
    project_scale = request.args.get("project_scale", type=str)
    project_status = request.args.get("project_status", type=str)
    project_amount = request.args.get("project_amount", type=str)
    keyword = (request.args.get("q", type=str) or "").strip()[:100]
    has_payments = request.args.get("has_payments", type=str) == 'true'
    has_orders = request.args.get("has_orders", type=str) == 'true'
    
    # 构建查询
    q = db.select(ProjectORM)
    
    # 如果要求仅显示有付款记录的项目
    if has_payments:
        from pear_admin.orms import OrderORM, PayORM
        # 使用 exists 子查询检查是否有关联的付款记录
        # Project -> Order -> Pay
        exists_query = db.select(PayORM.id).join(OrderORM).where(OrderORM.project_id == ProjectORM.id)
        q = q.where(exists_query.exists())
    
    # 如果要求仅显示有订单记录的项目
    if has_orders:
        from pear_admin.orms import OrderORM
        exists_query = db.select(OrderORM.id).where(OrderORM.project_id == ProjectORM.id)
        q = q.where(exists_query.exists())
    
    # 模糊搜索条件
    if keyword:
        q = q.where(or_(ProjectORM.project_name.contains(keyword, autoescape=True),
                        ProjectORM.project_full_name.contains(keyword, autoescape=True)))

    if project_name:

        q = q.where(ProjectORM.project_name.like(f"%{project_name}%"))
    if project_full_name:
        q = q.where(ProjectORM.project_full_name.like(f"%{project_full_name}%"))
    if project_scale:
        q = q.where(ProjectORM.project_scale.like(f"%{project_scale}%"))
    if project_status:
        q = q.where(ProjectORM.project_status.like(f"%{project_status}%"))
    if project_amount:
        q = q.where(cast(ProjectORM.project_amount, String).like(f"%{project_amount}%"))
    
    slim = request.args.get("mode") == "slim"
    if slim:
        q = q.options(load_only(ProjectORM.id, ProjectORM.project_name))
    else:
        q = q.options(selectinload(ProjectORM.attachment_list))
    pages: Pagination = db.paginate(q, page=page, per_page=per_page, error_out=False)
    
    return {
        "code": 0,
        "msg": "获取项目数据成功",
        "data": [{"id": item.id, "project_name": item.project_name} for item in pages.items]
                if slim else [item.json() for item in pages.items],
        "count": pages.total,
    }


@project_api.get("/<int:pid>")
@jwt_required()
def get_project(pid):
    project = db.session.get(ProjectORM, pid)
    if project is None:
        return {"code": -1, "msg": "项目不存在"}
    return {"code": 0, "msg": "获取项目详情成功", "data": project.json()}


_PROJECT_FIELDS = {
    "project_name", "project_full_name", "project_scale", "start_date", "end_date",
    "project_status", "project_amount", "project_audit_price_amount", "project_audit_amount", "create_at",
}


def _project_values(data):
    values = {}
    for key, value in data.items():
        if key not in _PROJECT_FIELDS:
            continue
        if value == "":
            value = None
        if key == "project_name" and (not isinstance(value, str) or not value.strip()):
            raise ValueError("项目名称不能为空")
        if value is not None:
            if key in ("start_date", "end_date"):
                value = datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
            elif key == "create_at":
                value = datetime.strptime(str(value).strip(), "%Y-%m-%d %H:%M:%S")
            elif key in ("project_amount", "project_audit_price_amount", "project_audit_amount"):
                value = Decimal(str(value))
                if not value.is_finite():
                    raise ValueError("金额必须为有效数字")
        values[key] = value
    return values


def _attachment_changes(raw, project_id=None):
    """Validate every item before mutating any project or attachment."""
    items = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(items, list):
        raise ValueError("附件必须为数组或 JSON 数组字符串")
    changes, seen = [], set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("附件条目格式错误")
        attachment = None
        aid = item.get("id")
        if aid not in (None, ""):
            if isinstance(aid, bool) or not str(aid).isdigit() or int(aid) < 1:
                raise ValueError("附件 ID 格式错误")
            aid = int(aid)
            if aid in seen:
                raise ValueError("附件 ID 重复")
            seen.add(aid)
            attachment = db.session.get(AttachmentORM, aid)
            if attachment is None:
                raise ValueError("附件不存在")
            if attachment.project_id != project_id and not (project_id is None and attachment.project_id is None):
                raise ValueError("附件不属于当前项目")
        code = item.get("code", attachment.attachment_code if attachment else None)
        if not isinstance(code, str) or not code.strip() or len(code) > 64:
            raise ValueError("附件编号不能为空且不能超过64个字符")
        if attachment:
            changes.append((attachment, {"attachment_code": code}))
            continue
        filename = item.get("filename") or item.get("name")
        path = item.get("file_path") or item.get("url")
        if not filename and isinstance(path, str):
            filename = path.split("?")[0].rstrip("/").rsplit("/", 1)[-1]
        name = item.get("name") or filename
        if not all(isinstance(v, str) and v.strip() for v in (filename, name, path)):
            raise ValueError("新附件需要文件名和文件路径")
        if len(filename) > 255 or len(name) > 255 or len(path) > 512:
            raise ValueError("附件文件名或路径过长")
        size = item.get("size", 0)
        if isinstance(size, bool) or not str(size).isdigit():
            raise ValueError("附件大小必须为非负整数")
        changes.append((None, dict(attachment_code=code, filename=filename,
                                  original_filename=name, file_path=path, file_size=int(size))))
    return changes


def _apply_attachments(project, changes):
    existing = list(project.attachment_list)
    retained = set()
    for attachment, values in changes:
        if attachment is None:
            db.session.add(AttachmentORM(project_id=project.id, **values))
        else:
            attachment.project_id = project.id
            attachment.attachment_code = values["attachment_code"]
            retained.add(attachment.id)
    for attachment in existing:
        if attachment.id not in retained:
            db.session.delete(attachment)


@project_api.post("/")
@jwt_required()
def create_project():
    try:
        data = request.get_json()
        if not isinstance(data, dict) or not data:
            return {"code": -1, "msg": "请求数据为空"}
        if not data.get("project_name"):
            return {"code": -1, "msg": "项目名称不能为空"}
        values = _project_values(data)
        changes = _attachment_changes(data["attachments"]) if "attachments" in data else None
        project = ProjectORM(**values)
        db.session.add(project)
        db.session.flush()
        if changes is not None:
            _apply_attachments(project, changes)
        db.session.commit()
        return {"code": 0, "msg": "新增项目成功", "data": {"id": project.id}}
    except Exception as exc:
        db.session.rollback()
        return {"code": -1, "msg": f"新增项目失败: {str(exc)}"}


@project_api.put("/<int:pid>")
@project_api.put("/")
@jwt_required()
def change_project(pid=None):
    try:
        data = request.get_json()
        if not isinstance(data, dict) or not data:
            return {"code": -1, "msg": "请求数据为空"}
        project = db.session.get(ProjectORM, data.get("id") or pid)
        if project is None:
            return {"code": -1, "msg": "项目不存在"}
        values = _project_values(data)
        changes = _attachment_changes(data["attachments"], project.id) if "attachments" in data else None
        for key, value in values.items():
            setattr(project, key, value)
        if changes is not None:
            _apply_attachments(project, changes)
        db.session.commit()
        return {"code": 0, "msg": "修改项目信息成功"}
    except Exception as exc:
        db.session.rollback()
        return {"code": -1, "msg": f"修改项目失败: {str(exc)}"}


@project_api.delete("/<int:pid>")
@jwt_required()
def del_project(pid):
    project_obj = ProjectORM.query.get(pid)
    if not project_obj:
        return {"code": -1, "msg": "项目不存在"}
    
    # 删除项目时，关联的附件也会被级联删除（因为设置了 ondelete="CASCADE"）
    project_obj.delete()
    return {"code": 0, "msg": "删除项目成功"}

