from datetime import datetime

import json

from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import cast, String

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
    
    # 构建查询
    q = db.select(ProjectORM)
    
    # 模糊搜索条件
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
    
    pages: Pagination = db.paginate(q, page=page, per_page=per_page, error_out=False)
    
    return {
        "code": 0,
        "msg": "获取项目数据成功",
        "data": [item.json() for item in pages.items],
        "count": pages.total,
    }


@project_api.post("/")
@jwt_required()
def create_project():
    data = request.get_json()
    if data.get("id"):
        del data["id"]
    
    # 保存附件数据（如果有）
    attachments_data = None
    if "attachments" in data:
        attachments_data = data.pop("attachments")
    
    # 处理日期字段
    if data.get("start_date"):
        data["start_date"] = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
    if data.get("end_date"):
        data["end_date"] = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
    
    # 处理金额字段
    if data.get("project_amount"):
        data["project_amount"] = float(data["project_amount"])
    
    # 创建项目
    project = ProjectORM(**data)
    project.save()
    
    # 处理附件数据
    if attachments_data:
      try:
        attachments_list = json.loads(attachments_data) if isinstance(attachments_data, str) else attachments_data
        if isinstance(attachments_list, list):
          for att_data in attachments_list:
            if att_data.get("code"):
              attachment_id = att_data.get("id")
              if attachment_id:
                # 更新现有附件记录，关联到项目
                attachment = AttachmentORM.query.get(attachment_id)
                if attachment:
                  attachment.project_id = project.id
                  attachment.attachment_code = att_data.get("code", attachment.attachment_code)
                  attachment.save()
              elif att_data.get("filename") or att_data.get("url"):
                # 创建新的附件记录
                attachment = AttachmentORM(
                  project_id=project.id,
                  attachment_code=att_data.get("code", ""),
                  filename=att_data.get("filename", att_data.get("name", "")),
                  original_filename=att_data.get("name", att_data.get("filename", "")),
                  file_path=att_data.get("url", ""),
                  file_size=att_data.get("size", 0)
                )
                attachment.save()
      except Exception as e:
        # 附件处理失败不影响项目创建
        pass
    
    return {"code": 0, "msg": "新增项目成功"}


@project_api.put("/<int:pid>")
@project_api.put("/")
@jwt_required()
def change_project(pid=None):
    data = request.get_json()
    pid = data.get("id") or pid
    
    project_obj = ProjectORM.query.get(pid)
    if not project_obj:
        return {"code": -1, "msg": "项目不存在"}
    
    # 保存附件数据（如果有）
    attachments_data = None
    if "attachments" in data:
        attachments_data = data.pop("attachments")
    
    for key, value in data.items():
        if key == "id":
            continue
        if key == "create_at" and value:
            value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        elif key == "start_date" and value:
            value = datetime.strptime(value, "%Y-%m-%d").date()
        elif key == "end_date" and value:
            value = datetime.strptime(value, "%Y-%m-%d").date()
        elif key == "project_amount" and value:
            value = float(value)
        setattr(project_obj, key, value)
    
    project_obj.save()
    
    # 处理附件数据
    if attachments_data is not None:
        try:
            attachments_list = json.loads(attachments_data) if isinstance(attachments_data, str) else attachments_data
            if isinstance(attachments_list, list):
                # 获取当前项目的所有附件ID
                existing_attachment_ids = {att.id for att in project_obj.attachment_list}
                new_attachment_ids = set()
                
                # 更新或创建附件记录
                for att_data in attachments_list:
                    attachment_id = att_data.get("id")
                    if attachment_id:
                        # 更新现有附件
                        attachment = AttachmentORM.query.get(attachment_id)
                        if attachment and attachment.project_id == pid:
                            attachment.attachment_code = att_data.get("code", attachment.attachment_code)
                            attachment.save()
                            new_attachment_ids.add(attachment_id)
                    elif att_data.get("code") and att_data.get("filename"):
                        # 创建新附件记录
                        attachment = AttachmentORM(
                            project_id=pid,
                            attachment_code=att_data.get("code", ""),
                            filename=att_data.get("filename", att_data.get("name", "")),
                            original_filename=att_data.get("name", att_data.get("filename", "")),
                            file_path=att_data.get("url", ""),
                            file_size=att_data.get("size", 0)
                        )
                        attachment.save()
                        new_attachment_ids.add(attachment.id)
                
                # 删除不在新列表中的附件
                to_delete_ids = existing_attachment_ids - new_attachment_ids
                if to_delete_ids:
                    AttachmentORM.query.filter(AttachmentORM.id.in_(to_delete_ids)).delete()
                    db.session.commit()
        except Exception as e:
            # 附件处理失败不影响项目更新
            pass
    
    return {"code": 0, "msg": "修改项目信息成功"}


@project_api.delete("/<int:pid>")
@jwt_required()
def del_project(pid):
    project_obj = ProjectORM.query.get(pid)
    if not project_obj:
        return {"code": -1, "msg": "项目不存在"}
    
    # 删除项目时，关联的附件也会被级联删除（因为设置了 ondelete="CASCADE"）
    project_obj.delete()
    return {"code": 0, "msg": "删除项目成功"}

