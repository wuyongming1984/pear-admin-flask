from datetime import datetime, date

from pear_admin.extensions import db

from ._base import BaseORM


class OrderORM(BaseORM):
    __tablename__ = "ums_order"

    id = db.Column(db.Integer, primary_key=True, comment="自增id")
    order_number = db.Column(db.String(64), nullable=False, unique=True, comment="订单编号")
    material_name = db.Column(db.String(128), nullable=False, comment="材料名称")
    project_name = db.Column(db.String(128), nullable=True, comment="项目名称")
    supplier_id = db.Column(
        db.Integer,
        db.ForeignKey("ums_supplier.id", ondelete="SET NULL"),
        nullable=True,
        comment="供应商ID"
    )
    supplier_contact_person = db.Column(db.String(64), nullable=True, comment="供应商联系人")
    contact_phone = db.Column(db.String(32), nullable=True, comment="联系电话")
    cutting_time = db.Column(db.Date, nullable=True, comment="下料时间")
    estimated_arrival_time = db.Column(db.Date, nullable=True, comment="预计到场时间")
    material_details = db.Column(db.Text, nullable=True, comment="材料明细")
    order_amount = db.Column(db.Numeric(18, 2), nullable=True, comment="订单金额")
    material_manager = db.Column(db.String(64), nullable=True, comment="材料负责人")
    sub_project_manager = db.Column(db.String(64), nullable=True, comment="分项目负责人")
    attachments = db.Column(db.Text, nullable=True, comment="附件")
    create_at = db.Column(
        db.DateTime,
        nullable=False,
        comment="创建时间",
        default=datetime.now,
    )

    # 关系属性（延迟导入避免循环依赖）
    supplier = db.relationship("SupplierORM", backref="orders", lazy="select")

    def json(self):
        import json as json_lib
        
        # 处理日期字段 - 可能是date/datetime对象或bytes类型
        def format_date(date_field):
            if not date_field:
                return None
            if isinstance(date_field, bytes):
                return date_field.decode('utf-8')
            elif hasattr(date_field, 'strftime'):
                return date_field.strftime("%Y-%m-%d")
            else:
                return str(date_field)
        
        def format_datetime(datetime_field):
            if not datetime_field:
                return None
            if isinstance(datetime_field, bytes):
                return datetime_field.decode('utf-8')
            elif hasattr(datetime_field, 'strftime'):
                return datetime_field.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return str(datetime_field)
        
        # 处理金额字段 - 可能是Decimal/float/bytes类型
        def format_amount(amount_field):
            if not amount_field:
                return None
            if isinstance(amount_field, bytes):
                return amount_field.decode('utf-8')
            else:
                return str(amount_field)
        
        # 解析附件数据
        attachments_data = []
        if self.attachments:
            try:
                attachments_data = json_lib.loads(self.attachments) if isinstance(self.attachments, str) else self.attachments
                if not isinstance(attachments_data, list):
                    attachments_data = []
            except:
                attachments_data = []
        
        # 获取关联的付款单信息
        pays_list = []
        total_payment_amount = 0  # 付款单金额合计
        try:
            # 通过 backref 获取关联的付款单
            if hasattr(self, 'pays') and self.pays:
                for pay in self.pays:
                    # 计算付款单金额合计 - 处理可能的bytes类型
                    if pay.current_payment_amount:
                        amount_val = pay.current_payment_amount
                        if isinstance(amount_val, bytes):
                            amount_val = amount_val.decode('utf-8')
                        total_payment_amount += float(amount_val)
                    
                    pays_list.append({
                        "id": pay.id,
                        "pay_number": pay.pay_number,
                        "current_payment_amount": format_amount(pay.current_payment_amount),
                        "payment_status": pay.payment_status,
                        "handler": pay.handler,
                        "payer_supplier_name": pay.payer.name if pay.payer else None,
                        "payee_supplier_name": pay.payee_supplier.name if pay.payee_supplier else None,
                        "create_at": format_datetime(pay.create_at)
                    })
        except Exception as e:
            # 如果关系未加载或出错，返回空列表
            pays_list = []
        
        # 计算订单余额 = 订单金额 - 付款单金额之和
        # 处理order_amount可能是bytes的情况
        order_amount_raw = self.order_amount
        if isinstance(order_amount_raw, bytes):
            order_amount_raw = order_amount_raw.decode('utf-8')
        order_amount_value = float(order_amount_raw) if order_amount_raw else 0
        order_balance = order_amount_value - total_payment_amount
        
        return {
            "id": self.id,
            "order_number": self.order_number,
            "material_name": self.material_name,
            "project_name": self.project_name,
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier.name if self.supplier else None,
            "supplier_contact_person": self.supplier_contact_person, # 使用新字段
            "contact_phone": self.contact_phone,
            "cutting_time": format_date(self.cutting_time),
            "estimated_arrival_time": format_date(self.estimated_arrival_time),
            "material_details": self.material_details,
            "order_amount": format_amount(self.order_amount),
            "order_balance": str(round(order_balance, 2)),  # 订单余额，保留两位小数
            "material_manager": self.material_manager,
            "sub_project_manager": self.sub_project_manager,
            "attachments": self.attachments,
            "attachments_list": attachments_data,
            "pays_list": pays_list,  # 关联的付款单列表
            "pays_count": len(pays_list),  # 付款单数量
            "is_order": True,  # 标记这是订单行
            "create_at": format_datetime(self.create_at),
        }
