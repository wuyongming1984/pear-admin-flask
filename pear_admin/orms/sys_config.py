from datetime import datetime
from pear_admin.extensions import db
from ._base import BaseORM

class SysConfigORM(BaseORM):
    """系统配置表"""
    __tablename__ = "sys_config"

    id = db.Column(db.Integer, primary_key=True, comment="自增id")
    key = db.Column(db.String(100), unique=True, nullable=False, comment="配置键")
    value = db.Column(db.Text, nullable=True, comment="配置值(JSON/String)")
    description = db.Column(db.String(255), nullable=True, comment="描述")
    
    create_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")
    update_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def json(self):
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "create_at": self.create_at.strftime("%Y-%m-%d %H:%M:%S") if self.create_at else None,
            "update_at": self.update_at.strftime("%Y-%m-%d %H:%M:%S") if self.update_at else None
        }
