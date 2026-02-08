from datetime import datetime

from pear_admin.extensions import db

from ._base import BaseORM


# 付款单与发票的中间关联表
pay_invoice_relation = db.Table(
    "pay_invoice_relation",
    db.Column("id", db.Integer, primary_key=True, autoincrement=True),
    db.Column("pay_id", db.Integer, db.ForeignKey("ums_pay.id", ondelete="CASCADE")),
    db.Column("invoice_id", db.Integer, db.ForeignKey("material_invoice.id", ondelete="CASCADE")),
    db.Column("create_at", db.DateTime, default=datetime.now)
)


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
    
    # 付款单位 - 关联付款单位表
    payer_supplier_id = db.Column(
        db.Integer,
        db.ForeignKey("ums_payer.id", ondelete="SET NULL"),
        nullable=True,
        comment="付款单位（关联付款单位ID）"
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
    
    # 附件
    attachments = db.Column(db.Text, nullable=True, comment="附件")
    
    # 附件ID (Legacy)
    fjid = db.Column(db.String(200), nullable=True, comment="附件ID")
    
    create_at = db.Column(
        db.DateTime,
        nullable=False,
        comment="创建时间",
        default=datetime.now,
    )

    # 关系属性
    order = db.relationship("OrderORM", backref="pays", lazy="select")
    payer = db.relationship(
        "PayerORM",
        foreign_keys=[payer_supplier_id],
        backref="pays",
        lazy="select"
    )
    payee_supplier = db.relationship(
        "SupplierORM",
        foreign_keys=[payee_supplier_id],
        backref="payee_pays",
        lazy="select"
    )
    
    # 与发票的多对多关系
    invoices = db.relationship(
        "MaterialInvoiceORM",
        secondary="pay_invoice_relation",
        backref="related_pays",
        lazy="select"
    )

    def json(self):
        import json as json_lib
        
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
        
        # 处理数值字段 - 可能是Decimal、bytes或其他类型
        def format_numeric(numeric_field):
            if numeric_field is None:
                return None
            if isinstance(numeric_field, bytes):
                return numeric_field.decode('utf-8')
            else:
                return str(numeric_field)
        
        # 解析附件数据
        from pear_admin.extensions import oss
        
        attachments_data = []
        if self.attachments:
            try:
                raw_attachments = json_lib.loads(self.attachments) if isinstance(self.attachments, str) else self.attachments
                if isinstance(raw_attachments, list):
                    for att in raw_attachments:
                        if isinstance(att, dict):
                            url = att.get('url')
                            if url:
                                # Sign the URL
                                signed_url = oss.generate_signed_url(url)
                                if signed_url:
                                    att['url'] = signed_url
                            attachments_data.append(att)
            except:
                attachments_data = []
        
        # 获取关联的发票列表
        invoices_list = []
        if self.invoices:
            for invoice in self.invoices:
                invoices_list.append({
                    "id": invoice.id,
                    "invoice_number": invoice.invoice_number,
                    "invoice_code": invoice.invoice_code,
                    "invoice_date": invoice.invoice_date.strftime("%Y-%m-%d") if invoice.invoice_date else None,
                    "total_amount": format_numeric(invoice.total_amount),
                    "seller_name": invoice.seller_name,
                    "file_path": invoice.file_path,
                })
        
        return {
            "id": self.id,
            "pay_number": self.pay_number,
            "order_id": self.order_id,
            "order_number": self.order.order_number if self.order else None,
            "order_amount": format_numeric(self.order.order_amount) if self.order else None,
            "project_name": self.order.project.project_name if self.order and self.order.project else None,
            "supplier_contact_person": self.order.supplier_contact_person if self.order else None,
            "payer_supplier_id": self.payer_supplier_id,
            "payer_supplier_name": self.payer.name if self.payer else None,
            "payee_supplier_id": self.payee_supplier_id,
            "payee_supplier_name": self.payee_supplier.name if self.payee_supplier else None,
            "payment_purpose": self.payment_purpose,
            "current_payment_amount": format_numeric(self.current_payment_amount),
            "invoice_amount": format_numeric(self.invoice_amount),
            "payment_status": self.payment_status,
            "handler": self.handler,
            "create_at": format_datetime(self.create_at),
            "attachments_list": attachments_data,
            "invoices_list": invoices_list,
        }

