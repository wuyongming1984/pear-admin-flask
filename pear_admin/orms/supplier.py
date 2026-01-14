from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from pear_admin.extensions import db

from ._base import BaseORM


class SupplierORM(BaseORM):
    __tablename__ = "ums_supplier"

    id = db.Column(db.Integer, primary_key=True, comment="自增id")
    type_id = db.Column(db.Integer, nullable=False, comment="供应商类型")

    name = db.Column(db.String(128), nullable=False, comment="供应商名称")
    contact_person = db.Column(db.String(128), nullable=False, comment="联系人")
    phone = db.Column(db.String(32), nullable=False, comment="联系电话")
    email = db.Column(db.String(64), nullable=True, comment="邮箱")
    bank_name = db.Column(db.String(128), nullable=False, comment="开户行名称")
    account_number = db.Column(db.String(128), nullable=False, comment="银行账号")

    address = db.Column(db.Text, nullable=True, comment="地址")
    remark = db.Column(db.Text, nullable=True, comment="备注")
    create_at = db.Column(
        db.DateTime,
        nullable=False,
        comment="创建时间",
        default=datetime.now,
    )




    def json(self):
        # 处理create_at字段 - 可能是datetime或bytes类型
        create_at_str = None
        if self.create_at:
            if isinstance(self.create_at, bytes):
                # 如果是bytes，直接解码为字符串
                create_at_str = self.create_at.decode('utf-8')
            elif hasattr(self.create_at, 'strftime'):
                # 如果是datetime对象
                create_at_str = self.create_at.strftime("%Y-%m-%d %H:%M:%S")
            else:
                # 其他情况，尝试转为字符串
                create_at_str = str(self.create_at)
        
        return {
            "id": self.id,
            "type_id": self.type_id,
            "name": self.name,
            "contact_person": self.contact_person,
            "phone": self.phone,
            "email": self.email,
            "bank_name": self.bank_name,
            "account_number": self.account_number,
            "address": self.address,
            "remark": self.remark,
            "create_at": create_at_str,
        }
