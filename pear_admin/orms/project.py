import json
from datetime import datetime

from pear_admin.extensions import db

from ._base import BaseORM


class ProjectORM(BaseORM):
    __tablename__ = "ums_project"

    id = db.Column(db.Integer, primary_key=True, comment="自增id")
    project_name = db.Column(db.String(128), nullable=False, comment="项目名称")
    project_full_name = db.Column(db.String(256), nullable=True, comment="项目全称")
    project_scale = db.Column(db.String(128), nullable=True, comment="项目规模")
    start_date = db.Column(db.Date, nullable=True, comment="开始日期")
    end_date = db.Column(db.Date, nullable=True, comment="结束日期")
    project_status = db.Column(db.String(32), nullable=True, comment="项目状态")
    project_amount = db.Column(db.Numeric(18, 2), nullable=True, comment="项目金额")
    attachments = db.Column(db.Text, nullable=True, comment="附件")
    create_at = db.Column(
        db.DateTime,
        nullable=False,
        comment="创建时间",
        default=datetime.now,
    )

    def json(self):
        # 获取关联的附件列表
        attachments_data = []
        try:
            if hasattr(self, 'attachment_list') and self.attachment_list:
                attachments_data = [attachment.json() for attachment in self.attachment_list]
        except Exception:
            # 如果附件表不存在或查询失败，返回空列表
            attachments_data = []
        
        return {
            "id": self.id,
            "project_name": self.project_name,
            "project_full_name": self.project_full_name,
            "project_scale": self.project_scale,
            "start_date": self.start_date.strftime("%Y-%m-%d") if self.start_date else None,
            "end_date": self.end_date.strftime("%Y-%m-%d") if self.end_date else None,
            "project_status": self.project_status,
            "project_amount": str(self.project_amount) if self.project_amount else None,
            "attachments": json.dumps(attachments_data, ensure_ascii=False) if attachments_data else None,  # 保持向后兼容
            "attachments_list": attachments_data,  # 新增附件列表字段
            "create_at": self.create_at.strftime("%Y-%m-%d %H:%M:%S") if self.create_at else None,
        }
