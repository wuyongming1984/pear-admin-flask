from datetime import datetime

from pear_admin.extensions import db

from ._base import BaseORM


class PayerORM(BaseORM):
    __tablename__ = "ums_payer"

    id = db.Column(db.Integer, primary_key=True, comment="自增id")
    type_id = db.Column(db.Integer, nullable=False, comment="付款单位类型(1:单位, 2:个人)")
    name = db.Column(db.String(128), nullable=False, comment="付款单位名称")
    bank_name = db.Column(db.String(128), nullable=True, comment="开户行")
    account_number = db.Column(db.String(128), nullable=True, comment="账号")
    
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
            "bank_name": self.bank_name,
            "account_number": self.account_number,
            "remark": self.remark,
            "create_at": create_at_str
        }
