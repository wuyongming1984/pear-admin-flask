from datetime import datetime

from pear_admin.extensions import db

from ._base import BaseORM


class PayORM(BaseORM):
    __tablename__ = "ums_pay"

    id = db.Column(db.Integer, primary_key=True, comment="自增id")
    pay_number = db.Column(db.String(64), nullable=False, unique=True, comment="付款单编号")
    
    # 关联订单ID
    order_id = db.Column(
        db.Integer,
        db.ForeignKey("ums_order.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联订单ID"
    )
    
    # 付款单位 - 关联供应商ID
    payer_supplier_id = db.Column(
        db.Integer,
        db.ForeignKey("ums_supplier.id", ondelete="SET NULL"),
        nullable=True,
        comment="付款单位（关联供应商ID）"
    )
    
    # 收款单位 - 关联供应商ID
    payee_supplier_id = db.Column(
        db.Integer,
        db.ForeignKey("ums_supplier.id", ondelete="SET NULL"),
        nullable=True,
        comment="收款单位（关联供应商ID）"
    )
    
    # 付款用途
    payment_purpose = db.Column(db.Text, nullable=True, comment="付款用途")
    
    # 本次付款金额
    current_payment_amount = db.Column(db.Numeric(18, 2), nullable=True, comment="本次付款金额")
    
    # 开票金额
    invoice_amount = db.Column(db.Numeric(18, 2), nullable=True, comment="开票金额")
    
    # 付款状态
    payment_status = db.Column(db.String(32), nullable=True, comment="付款状态")
    
    # 经办人
    handler = db.Column(db.String(64), nullable=True, comment="经办人")
    
    create_at = db.Column(
        db.DateTime,
        nullable=False,
        comment="创建时间",
        default=datetime.now,
    )

    # 关系属性
    order = db.relationship("OrderORM", backref="pays", lazy="select")
    payer_supplier = db.relationship(
        "SupplierORM",
        foreign_keys=[payer_supplier_id],
        backref="payer_pays",
        lazy="select"
    )
    payee_supplier = db.relationship(
        "SupplierORM",
        foreign_keys=[payee_supplier_id],
        backref="payee_pays",
        lazy="select"
    )

    def json(self):
        return {
            "id": self.id,
            "pay_number": self.pay_number,
            "order_id": self.order_id,
            "order_number": self.order.order_number if self.order else None,
            "payer_supplier_id": self.payer_supplier_id,
            "payer_supplier_name": self.payer_supplier.name if self.payer_supplier else None,
            "payee_supplier_id": self.payee_supplier_id,
            "payee_supplier_name": self.payee_supplier.name if self.payee_supplier else None,
            "payment_purpose": self.payment_purpose,
            "current_payment_amount": str(self.current_payment_amount) if self.current_payment_amount else None,
            "invoice_amount": str(self.invoice_amount) if self.invoice_amount else None,
            "payment_status": self.payment_status,
            "handler": self.handler,
            "create_at": self.create_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
