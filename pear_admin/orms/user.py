from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from pear_admin.extensions import db

from ._base import BaseORM


class UserORM(BaseORM):
    __tablename__ = "ums_user"

    id = db.Column(db.Integer, primary_key=True, comment="自增id")
    nickname = db.Column(db.String(128), nullable=False, comment="昵称")
    username = db.Column(db.String(128), nullable=False, comment="登录名")
    password_hash = db.Column(db.String(256), nullable=False, comment="登录密码")
    mobile = db.Column(db.String(32), nullable=False, comment="手机")
    email = db.Column(db.String(64), nullable=False, comment="邮箱")
    avatar = db.Column(db.Text, comment="头像地址")
    create_at = db.Column(
        db.DateTime,
        nullable=False,
        comment="创建时间",
        default=datetime.now,
    )
    department_id = db.Column(
        db.Integer, db.ForeignKey("ums_department.id"), default=1, comment="部门id"
    )

    role_list = db.relationship(
        "RoleORM",
        secondary="ums_user_role",
        backref=db.backref("user"),
        lazy="dynamic",
    )

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
            "username": self.username,
            "nickname": self.nickname,
            "mobile": self.mobile,
            "email": self.email,
            "create_at": format_datetime(self.create_at),
        }

    @property
    def password(self):
        return self.password_hash

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password=password)
