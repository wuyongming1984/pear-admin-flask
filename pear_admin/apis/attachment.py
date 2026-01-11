from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from pear_admin.extensions import db
from pear_admin.orms import AttachmentORM

attachment_api = Blueprint("attachment", __name__, url_prefix="/attachment")


@attachment_api.delete("/<int:aid>")
@jwt_required()
def delete_attachment(aid):
    attachment = AttachmentORM.query.get(aid)
    if not attachment:
        return {"code": -1, "msg": "附件不存在"}
    
    attachment.delete()
    return {"code": 0, "msg": "删除附件成功"}


@attachment_api.get("/project/<int:pid>")
@jwt_required()
def get_project_attachments(pid):
    attachments = AttachmentORM.query.filter_by(project_id=pid).all()
    return {
        "code": 0,
        "msg": "获取附件列表成功",
        "data": [att.json() for att in attachments]
    }

