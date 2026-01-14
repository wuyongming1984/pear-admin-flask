from datetime import datetime

from pear_admin.extensions import db

from ._base import BaseORM


class AttachmentORM(BaseORM):
    __tablename__ = "ums_attachment"

    id = db.Column(db.Integer, primary_key=True, comment="自增id")
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("ums_project.id", ondelete="CASCADE"),
        nullable=False,
        comment="项目ID"
    )
    attachment_code = db.Column(db.String(64), nullable=False, comment="附件编号")
    filename = db.Column(db.String(255), nullable=False, comment="文件名")
    original_filename = db.Column(db.String(255), nullable=False, comment="原始文件名")
    file_path = db.Column(db.String(512), nullable=False, comment="文件路径")
    file_size = db.Column(db.BigInteger, nullable=False, comment="文件大小（字节）")
    create_at = db.Column(
        db.DateTime,
        nullable=False,
        comment="创建时间",
        default=datetime.now,
    )

    # 关系属性
    project = db.relationship("ProjectORM", backref="attachment_list")

    def json(self):
        # 处理datetime字段 - 可能是datetime对象或bytes类型
        def format_datetime(datetime_field):
            if not datetime_field:
                return None
            if isinstance(datetime_field, bytes):
                return datetime_field.decode('utf-8')
            elif hasattr(datetime_field, 'strftime'):
                return datetime_field.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return str(datetime_field)
        
        return {
            "id": self.id,
            "project_id": self.project_id,
            "code": self.attachment_code,
            "name": self.original_filename,
            "filename": self.filename,
            "url": self.file_path,
            "size": self.file_size,
            "create_at": format_datetime(self.create_at),
        }

