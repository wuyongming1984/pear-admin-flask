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
                    # 计算付款单金额合计
                    if pay.current_payment_amount:
                        total_payment_amount += float(pay.current_payment_amount)
                    
                    pays_list.append({
                        "id": pay.id,
                        "pay_number": pay.pay_number,
                        "current_payment_amount": str(pay.current_payment_amount) if pay.current_payment_amount else None,
                        "payment_status": pay.payment_status,
                        "handler": pay.handler,
                        "payer_supplier_name": pay.payer_supplier.name if pay.payer_supplier else None,
                        "payee_supplier_name": pay.payee_supplier.name if pay.payee_supplier else None,
                        "create_at": pay.create_at.strftime("%Y-%m-%d %H:%M:%S") if pay.create_at else None
                    })
        except Exception as e:
            # 如果关系未加载或出错，返回空列表
            pays_list = []
        
        # 计算订单余额 = 订单金额 - 付款单金额之和
        order_amount_value = float(self.order_amount) if self.order_amount else 0
        order_balance = order_amount_value - total_payment_amount
        
        return {
            "id": self.id,
            "order_number": self.order_number,
            "material_name": self.material_name,
            "project_name": self.project_name,
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier.name if self.supplier else None,
            "supplier_contact_person": self.supplier.contact_person if self.supplier else None,
            "contact_phone": self.contact_phone,
            "cutting_time": self.cutting_time.strftime("%Y-%m-%d") if self.cutting_time else None,
            "estimated_arrival_time": self.estimated_arrival_time.strftime("%Y-%m-%d") if self.estimated_arrival_time else None,
            "material_details": self.material_details,
            "order_amount": str(self.order_amount) if self.order_amount else None,
            "order_balance": str(round(order_balance, 2)),  # 订单余额，保留两位小数
            "material_manager": self.material_manager,
            "sub_project_manager": self.sub_project_manager,
            "attachments": self.attachments,
            "attachments_list": attachments_data,
            "pays_list": pays_list,  # 关联的付款单列表
            "pays_count": len(pays_list),  # 付款单数量
            "is_order": True,  # 标记这是订单行
            "create_at": self.create_at.strftime("%Y-%m-%d %H:%M:%S") if self.create_at else None,
        }
