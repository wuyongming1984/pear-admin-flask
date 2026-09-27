"""Validation shared by system administration forms."""
from functools import wraps
from flask import request, current_app
from sqlalchemy.exc import SQLAlchemyError
from pear_admin.extensions import db


def validated(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (ValueError, TypeError) as exc:
            db.session.rollback()
            return {"code": -1, "success": False, "msg": str(exc) or "参数格式错误"}
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("系统数据保存失败")
            return {"code": -1, "success": False, "msg": "保存失败，请检查重复或关联数据后重试"}
    return wrapped


def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("请提交有效的表单数据")
    return dict(data)


def required(data, *keys):
    for key in keys:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("必填内容不能为空")
        data[key] = value.strip()


def record(model, identity):
    try:
        identity = int(identity)
    except (ValueError, TypeError):
        raise ValueError("记录ID无效")
    item = db.session.get(model, identity)
    if item is None:
        raise ValueError("记录不存在或已删除，请刷新列表")
    return item


def parent_id(model, value, identity=None):
    pid = int(value or 0)
    visited = {int(identity)} if identity else set()
    current = pid
    while current:
        if current in visited:
            raise ValueError("上级不能是自身或下级节点")
        visited.add(current)
        parent = record(model, current)
        current = parent.pid or 0
    return pid


def selected(model, value):
    if value is None:
        raise ValueError("请选择有效的授权列表")
    values = value.split(",") if isinstance(value, str) else value
    if not isinstance(values, list):
        raise ValueError("授权列表格式错误")
    ids = {int(item) for item in values if str(item).strip()}
    items = db.session.scalars(db.select(model).where(model.id.in_(ids))).all()
    if len(items) != len(ids):
        raise ValueError("授权项已失效，请刷新后重试")
    return items


def nested(items, serializer):
    by_parent = {}
    for item in items:
        by_parent.setdefault(item.pid or 0, []).append(item)
    def children(pid, seen):
        result = []
        for item in by_parent.get(pid, []):
            if item.id in seen:
                continue
            data = serializer(item)
            data["children"] = children(item.id, seen | {item.id})
            if data["children"]:
                data["isParent"] = True
            result.append(data)
        return result
    return children(0, set())
