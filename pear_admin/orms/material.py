from datetime import datetime
from pear_admin.extensions import db
from ._base import BaseORM

class MaterialPlanningORM(BaseORM):
    """材料策划"""
    __tablename__ = "material_planning"

    id = db.Column(db.Integer, primary_key=True, comment="自增id")
    project_id = db.Column(db.Integer, db.ForeignKey("ums_project.id"), nullable=True, comment="关联项目ID")
    material_name = db.Column(db.String(128), nullable=False, comment="材料名称")
    material_spec = db.Column(db.String(128), nullable=True, comment="规格型号")
    material_unit = db.Column(db.String(32), nullable=True, comment="单位")
    planned_total_quantity = db.Column(db.Numeric(18, 2), default=0, comment="策划总数")
    planned_remaining_quantity = db.Column(db.Numeric(18, 2), default=0, comment="策划余量")
    planned_price = db.Column(db.Numeric(18, 2), default=0, comment="策划单价")
    supplier_id = db.Column(db.Integer, db.ForeignKey("ums_supplier.id"), nullable=True, comment="拟定供应商ID")
    batch_number = db.Column(db.String(64), nullable=True, comment="批次号")
    
    # 关联
    project = db.relationship("ProjectORM", backref="material_plannings")
    supplier = db.relationship("SupplierORM", backref="material_plannings")
    
    create_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")

    def json(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "project_name": self.project.project_name if self.project else "",
            "material_name": self.material_name,
            "material_spec": self.material_spec,
            "material_unit": self.material_unit,
            "planned_total_quantity": str(self.planned_total_quantity),
            "planned_remaining_quantity": str(self.planned_remaining_quantity),
            "planned_price": str(self.planned_price),
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier.name if self.supplier else "",
            "batch_number": self.batch_number or "",
            "create_at": self.create_at.strftime("%Y-%m-%d %H:%M:%S") if self.create_at else None
        }

class MaterialInboundORM(BaseORM):
    """拟入库计划/任务"""
    __tablename__ = "material_inbound"
    
    id = db.Column(db.Integer, primary_key=True, comment="自增id")
    project_id = db.Column(db.Integer, db.ForeignKey("ums_project.id"), nullable=True, comment="关联项目ID")
    
    batch_number = db.Column(db.String(64), nullable=True, comment="批次号")
    batch_sub_number = db.Column(db.String(64), nullable=True, comment="批次分号") # e.g. 批次-0520-001
    
    material_name = db.Column(db.String(128), nullable=False, comment="材料名称")
    material_spec = db.Column(db.String(128), nullable=True, comment="规格型号")
    material_unit = db.Column(db.String(64), nullable=True, comment="单位")
    
    supplier_id = db.Column(db.Integer, db.ForeignKey("ums_supplier.id"), nullable=True, comment="供应商ID")
    
    inbound_quantity = db.Column(db.Numeric(18, 2), default=0, comment="入库量")
    inbound_price = db.Column(db.Numeric(18, 2), default=0, comment="入库单价")
    inbound_total_amount = db.Column(db.Numeric(18, 2), default=0, comment="入库合价")
    
    status = db.Column(db.String(32), default="pending", comment="状态: pending(拟入库), completed(已入库)")
    
    create_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")
    
    invoice_id = db.Column(db.Integer, db.ForeignKey("material_invoice.id"), nullable=True, comment="关联发票ID")
    
    project = db.relationship("ProjectORM", backref="material_inbounds")
    supplier = db.relationship("SupplierORM", backref="material_inbounds")
    invoice = db.relationship("MaterialInvoiceORM", backref="inbounds")

    def json(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "project_name": self.project.project_name if self.project else "",
            "batch_number": self.batch_number,
            "batch_sub_number": self.batch_sub_number,
            "material_name": self.material_name,
            "material_spec": self.material_spec,
            "material_unit": self.material_unit,
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier.name if self.supplier else "",
            "inbound_quantity": str(self.inbound_quantity),
            "inbound_price": str(self.inbound_price),
            "status": self.status,
            "invoice_id": self.invoice_id,
            "invoice_number": self.invoice.invoice_number if self.invoice else "",
            "invoice_amount": str(self.invoice.total_amount) if self.invoice else "",
            "invoice_category": self.invoice.invoice_category if self.invoice else "",
            "invoice_file_path": self.invoice.file_path if self.invoice else "",
            "invoice_file_type": self.invoice.file_type if self.invoice else "",
            "create_at": self.create_at.strftime("%Y-%m-%d %H:%M:%S") if self.create_at else None
        }

class MaterialInventoryORM(BaseORM):
    """库存台账"""
    __tablename__ = "material_inventory"
    
    id = db.Column(db.Integer, primary_key=True, comment="自增id")
    project_id = db.Column(db.Integer, db.ForeignKey("ums_project.id"), nullable=True, comment="关联项目ID")
    
    material_name = db.Column(db.String(128), nullable=False, comment="材料名称")
    material_spec = db.Column(db.String(128), nullable=True, comment="规格型号")
    material_unit = db.Column(db.String(64), nullable=True, comment="单位")
    
    current_stock = db.Column(db.Numeric(18, 2), default=0, comment="当前库存")
    
    latest_price = db.Column(db.Numeric(18, 2), default=0, comment="最近入库单价")
    total_value = db.Column(db.Numeric(18, 2), default=0, comment="库存总值(估算)")
    
    supplier_id = db.Column(db.Integer, db.ForeignKey("ums_supplier.id"), nullable=True, comment="主要供应商ID")
    seller_id = db.Column(db.Integer, db.ForeignKey("ums_supplier.id"), nullable=True, comment="销售商ID")

    seller_price = db.Column(db.Numeric(18, 2), default=0, comment="销售单价(含税)")
    seller_quantity = db.Column(db.Numeric(18, 2), default=0, comment="销售数量")
    profit_ratio = db.Column(db.Numeric(10, 2), default=1.05, comment="利润系数")
    
    tax_rate = db.Column(db.Numeric(10, 4), default=0, comment="税率")
    tax_amount = db.Column(db.Numeric(18, 2), default=0, comment="税额")
    price_no_tax = db.Column(db.Numeric(18, 2), default=0, comment="不含税单价")
    
    related_invoice_number = db.Column(db.String(64), nullable=True, comment="关联单号")
    latest_invoice_id = db.Column(db.Integer, db.ForeignKey("material_invoice.id"), nullable=True, comment="最近一次入库关联发票ID")
    
    create_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")
    
    project = db.relationship("ProjectORM", backref="material_inventories")
    supplier = db.relationship("SupplierORM", foreign_keys=[supplier_id], backref="material_inventories")
    seller = db.relationship("SupplierORM", foreign_keys=[seller_id], backref="seller_inventories")
    latest_invoice = db.relationship("MaterialInvoiceORM", foreign_keys=[latest_invoice_id])

    def json(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "project_name": self.project.project_name if self.project else "",
            "material_name": self.material_name,
            "material_spec": self.material_spec,
            "material_unit": self.material_unit,
            "current_stock": str(self.current_stock),
            "latest_price": str(self.latest_price),
            "total_value": str(self.total_value),
            "supplier_name": self.supplier.name if self.supplier else "",
            "seller_id": self.seller_id,
            "seller_name": self.seller.name if self.seller else "", # Return name from relationship
            "seller_price": str(self.seller_price),
            "seller_quantity": str(self.seller_quantity),
            "profit_ratio": str(self.profit_ratio) if self.profit_ratio else "1.05",
            "tax_rate": str(self.tax_rate) if self.tax_rate is not None else "0",
            "tax_amount": str(self.tax_amount),
            "price_no_tax": str(self.price_no_tax),
            "related_invoice_number": self.latest_invoice.invoice_number if self.latest_invoice else (self.related_invoice_number or ""),
            "latest_invoice_id": self.latest_invoice_id,
           "latest_invoice_number": self.latest_invoice.invoice_number if self.latest_invoice else "",
            "latest_invoice_file_path": self.latest_invoice.file_path if self.latest_invoice else "",
            "create_at": self.create_at.strftime("%Y-%m-%d %H:%M:%S") if self.create_at else None
        }

class MaterialOutboundORM(BaseORM):
    """拟出库计划"""
    __tablename__ = "material_outbound"
    
    id = db.Column(db.Integer, primary_key=True, comment="自增id")
    
    # 核心关联
    inventory_id = db.Column(db.Integer, db.ForeignKey("material_inventory.id"), nullable=True, comment="关联库存ID")
    invoice_id = db.Column(db.Integer, db.ForeignKey("material_invoice.id"), nullable=True, comment="关联发票ID")
    
    # 快照/冗余字段 (Snapshot/Redundant fields) - Added 2026-01-30
    project_id = db.Column(db.Integer, db.ForeignKey("ums_project.id"), nullable=True, comment="关联项目ID")
    material_name = db.Column(db.String(128), nullable=True, comment="材料名称")
    material_spec = db.Column(db.String(128), nullable=True, comment="规格型号")
    material_unit = db.Column(db.String(32), nullable=True, comment="单位")
    seller_price = db.Column(db.Numeric(18, 2), default=0, comment="销售单价(含税)")
    seller_quantity = db.Column(db.Numeric(18, 2), default=0, comment="销售数量")
    completed_sales_quantity = db.Column(db.Numeric(18, 2), default=0, comment="完成销售数量")
    seller_id = db.Column(db.Integer, db.ForeignKey("ums_supplier.id"), nullable=True, comment="销售商ID")
    tax_rate = db.Column(db.Numeric(10, 4), default=0, comment="税率")

    # 批次与状态
    batch_number = db.Column(db.String(64), nullable=True, comment="批次号")
    status = db.Column(db.String(32), default="pending", comment="状态: pending(拟出库), completed(已出库)")
    create_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")
    
    # 关系
    inventory = db.relationship("MaterialInventoryORM", backref="outbounds")
    invoice = db.relationship("MaterialInvoiceORM", backref="outbounds")
    seller = db.relationship("SupplierORM", foreign_keys=[seller_id], backref="outbound_seller")

    def json(self):
        inv = self.inventory
        # Priority: Self fields -> Inventory fields -> defaults
        
        # Helper to get numeric string
        def fmt(val):
            return str(val) if val is not None else "0"
            
        # Snapshot Detection: If material_name is snapshotted, trust other snapshot fields even if 0
        has_snapshot = self.material_name is not None
        
        m_name = self.material_name if has_snapshot else (inv.material_name if inv else "")
        m_spec = self.material_spec if has_snapshot else (inv.material_spec if inv else "")
        m_unit = self.material_unit if has_snapshot else (inv.material_unit if inv else "")
        p_id = self.project_id if has_snapshot else (inv.project_id if inv else None)
        s_qty = self.seller_quantity if has_snapshot else (inv.seller_quantity if inv else 0)
        s_price = self.seller_price if has_snapshot else (inv.seller_price if inv else 0)
        s_id = self.seller_id if has_snapshot else (inv.seller_id if inv else None)
        t_rate = self.tax_rate if has_snapshot else (inv.tax_rate if inv else 0)
        
        # Calculate derived values if needed
        p_no_tax = float(s_price) / (1 + float(t_rate)) if float(t_rate) > 0 else float(s_price)
        t_amount = float(s_price) - p_no_tax
        
        return {
            "id": self.id,
            "inventory_id": self.inventory_id,
            "batch_number": self.batch_number or "",
            "status": self.status,
            "create_at": self.create_at.strftime("%Y-%m-%d %H:%M:%S") if self.create_at else None,
            
            # 动态获取库存详情
            "project_name": inv.project.project_name if inv and inv.project else "",
            "material_name": m_name,
            "material_spec": m_spec,
            "material_unit": m_unit,
            
            # 使用库存的销售数量作为"计划出库量" (Or use self.seller_quantity if snapshot taken)
            "outbound_quantity": fmt(s_qty),
            
            "seller_price": fmt(s_price),
            "seller_quantity": fmt(s_qty),
            "completed_sales_quantity": fmt(self.completed_sales_quantity or 0),
            "seller_id": s_id,
            "seller_name": self.seller.name if self.seller else (inv.seller.name if inv and inv.seller else ""),
            
            # 补充字段
            "tax_rate": str(t_rate),
            "price_no_tax": "{:.2f}".format(p_no_tax),
            "tax_amount": "{:.2f}".format(t_amount),
            
            # 发票相关
            "project_id": p_id,
            "invoice_id": self.invoice_id,
            "invoice_number": self.invoice.invoice_number if self.invoice else "",
            "invoice_amount": str(self.invoice.total_amount) if self.invoice else "",
            "invoice_category": self.invoice.invoice_category if self.invoice else "",
            "invoice_file_path": self.invoice.file_path if self.invoice else "",
            "invoice_file_type": self.invoice.file_type if self.invoice else "",
            "invoice_buyer_name": self.invoice.buyer_name if self.invoice else "",
            "invoice_seller_name": self.invoice.seller_name if self.invoice else "",
            "inbound_invoice_number": inv.latest_invoice.invoice_number if inv and inv.latest_invoice else "",
            "inbound_invoice_file_path": inv.latest_invoice.file_path if inv and inv.latest_invoice else ""
        }

class MaterialInvoiceORM(BaseORM):
    """发票库"""
    __tablename__ = "material_invoice"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="自增id")
    project_id = db.Column(db.Integer, db.ForeignKey("ums_project.id"), nullable=True, comment="关联项目ID")
    supplier_id = db.Column(db.Integer, db.ForeignKey("ums_supplier.id"), nullable=True, comment="关联供应商ID")
    
    invoice_number = db.Column(db.String(64), nullable=True, comment="发票号码")
    invoice_code = db.Column(db.String(64), nullable=True, comment="发票代码")
    invoice_date = db.Column(db.Date, nullable=True, comment="开票日期")
    
    buyer_name = db.Column(db.String(128), nullable=True, comment="购买方名称")
    buyer_tax_num = db.Column(db.String(64), nullable=True, comment="购买方税号")
    seller_name = db.Column(db.String(128), nullable=True, comment="销售方名称")
    seller_tax_num = db.Column(db.String(64), nullable=True, comment="销售方税号")
    
    tax_rate = db.Column(db.Numeric(5, 2), default=0, comment="税率")
    tax_amount = db.Column(db.Numeric(18, 2), default=0, comment="合计税额")
    total_amount = db.Column(db.Numeric(18, 2), default=0, comment="价税合计")
    amount_in_words = db.Column(db.String(128), nullable=True, comment="价税合计(大写)")
    
    details_json = db.Column(db.Text, nullable=True, comment="明细JSON")
    
    # 基础信息增强
    invoice_type = db.Column(db.String(64), nullable=True, comment="发票种类")
    invoice_name = db.Column(db.String(128), nullable=True, comment="发票名称") # InvoiceTypeOrg
    check_code = db.Column(db.String(128), nullable=True, comment="校验码")
    machine_num = db.Column(db.String(64), nullable=True, comment="机器号码")
    password_area = db.Column(db.Text, nullable=True, comment="密码区")
    
    province = db.Column(db.String(64), nullable=True, comment="省")
    city = db.Column(db.String(64), nullable=True, comment="市")
    
    # 买卖方详细信息
    buyer_address_phone = db.Column(db.String(255), nullable=True, comment="购买方地址及电话")
    buyer_bank_account = db.Column(db.String(255), nullable=True, comment="购买方开户行及账号")
    seller_address_phone = db.Column(db.String(255), nullable=True, comment="销售方地址及电话")
    seller_bank_account = db.Column(db.String(255), nullable=True, comment="销售方开户行及账号")
    
    # 业务信息
    remarks = db.Column(db.Text, nullable=True, comment="备注")
    payee = db.Column(db.String(64), nullable=True, comment="收款人")
    checker = db.Column(db.String(64), nullable=True, comment="复核")
    drawer = db.Column(db.String(64), nullable=True, comment="开票人")
    
    # 分类和抵扣信息
    invoice_category = db.Column(db.String(64), nullable=True, comment="发票大类")
    deductible = db.Column(db.String(64), nullable=True, comment="可否抵扣")
    
    # 文件相关字段
    file_path = db.Column(db.String(500), nullable=True, comment="文件存储路径")
    file_name = db.Column(db.String(200), nullable=True, comment="原始文件名")
    file_type = db.Column(db.String(20), nullable=True, comment="文件类型(pdf/jpg/png)")
    
    # OCR相关字段
    ocr_status = db.Column(db.String(20), default='pending', comment="OCR状态: pending/processing/completed/failed")
    ocr_result = db.Column(db.Text, nullable=True, comment="OCR原始结果JSON")
    ocr_error = db.Column(db.Text, nullable=True, comment="OCR错误信息")
    
    create_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")
    update_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    # 关联
    project = db.relationship("ProjectORM", backref="material_invoices")
    supplier = db.relationship("SupplierORM", backref="material_invoices")
    details = db.relationship("MaterialInvoiceDetailORM", backref="invoice", cascade="all, delete-orphan")

    def _get_signed_url(self):
        """Generate signed URL for private OSS files"""
        if not self.file_path:
            return None
        
        # If file is stored locally, return as-is
        if not self.file_path.startswith('http'):
            return self.file_path
        
        # For OSS files, generate signed URL
        try:
            from pear_admin.extensions import oss
            from flask import current_app
            
            current_app.logger.info(f"[Invoice {self.id}] Attempting to generate signed URL for: {self.file_path}")
            
            if not oss:
                current_app.logger.error(f"[Invoice {self.id}] OSS extension not found")
                return self.file_path
            
            if not oss.bucket:
                current_app.logger.error(f"[Invoice {self.id}] OSS bucket not initialized")
                return self.file_path
            
            # Generate signed URL with 1 hour expiration
            # Force inline disposition for preview instead of download
            signed_url = oss.generate_signed_url(self.file_path, expires=3600, params={'response-content-disposition': 'inline'})
            
            if signed_url:
                current_app.logger.info(f"[Invoice {self.id}] Successfully generated signed URL (length: {len(signed_url)})")
                return signed_url
            else:
                current_app.logger.error(f"[Invoice {self.id}] generate_signed_url returned None")
                return self.file_path
                
        except Exception as e:
            # Fallback to original path on error
            from flask import current_app
            current_app.logger.error(f"[Invoice {self.id}] Exception in _get_signed_url: {e}", exc_info=True)
            return self.file_path

    def json(self):
        # 构造明细列表
        details_list = [d.json() for d in self.details]
        import json
        
        return {
            "id": self.id,
            "project_id": self.project_id,
            "project_name": self.project.project_name if self.project else "",
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier.name if self.supplier else "",
            "invoice_number": self.invoice_number,
            "invoice_code": self.invoice_code,
            "invoice_date": self.invoice_date.strftime("%Y-%m-%d") if self.invoice_date else None,
            "buyer_name": self.buyer_name,
            "buyer_tax_num": self.buyer_tax_num,
            "buyer_address_phone": self.buyer_address_phone,
            "buyer_bank_account": self.buyer_bank_account,
            
            "seller_name": self.seller_name,
            "seller_tax_num": self.seller_tax_num,
            "seller_address_phone": self.seller_address_phone,
            "seller_bank_account": self.seller_bank_account,
            
            "invoice_type": self.invoice_type,
            "invoice_name": self.invoice_name,
            "check_code": self.check_code,
            "machine_num": self.machine_num,
            "password_area": self.password_area,
            "province": self.province,
            "city": self.city,
            "remarks": self.remarks,
            "payee": self.payee,
            "checker": self.checker,
            "drawer": self.drawer,
            "invoice_category": self.invoice_category,
            "deductible": self.deductible,

            "tax_rate": str(self.tax_rate) if self.tax_rate else "0",
            "tax_amount": str(self.tax_amount) if self.tax_amount else "0",
            "total_amount": str(self.total_amount) if self.total_amount else "0",
            "amount_in_words": self.amount_in_words,
            "details": details_list,
            # 兼容旧逻辑，同时也返回JSON字符串
            "details_json": json.dumps(details_list, ensure_ascii=False),
            "file_path": self.file_path,
            "file_url": self._get_signed_url(),  # Generate signed URL for private OSS files
            "file_name": self.file_name,
            "file_type": self.file_type,
            "ocr_status": self.ocr_status,
            "ocr_result": self.ocr_result,
            "ocr_error": self.ocr_error,
            "create_at": self.create_at.strftime("%Y-%m-%d %H:%M:%S") if self.create_at else None,
            "update_at": self.update_at.strftime("%Y-%m-%d %H:%M:%S") if self.update_at else None
        }

class MaterialInvoiceDetailORM(BaseORM):
    """发票明细"""
    __tablename__ = "material_invoice_detail"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="自增id")
    invoice_id = db.Column(db.Integer, db.ForeignKey("material_invoice.id"), nullable=False, comment="关联发票ID")
    
    name = db.Column(db.String(255), nullable=True, comment="货物或应税劳务名称")
    spec = db.Column(db.String(128), nullable=True, comment="规格型号")
    unit = db.Column(db.String(32), nullable=True, comment="单位")
    quantity = db.Column(db.Numeric(18, 4), default=0, comment="数量")
    price = db.Column(db.Numeric(18, 4), default=0, comment="单价")
    amount = db.Column(db.Numeric(18, 2), default=0, comment="金额")
    tax_rate = db.Column(db.String(32), default="0", comment="税率") # 可能是 '13%' 或 '免税'
    tax_amount = db.Column(db.Numeric(18, 2), default=0, comment="税额")
    
    create_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")

    def json(self):
        return {
            "id": self.id,
            "name": self.name,
            "spec": self.spec,
            "unit": self.unit,
            "quantity": str(self.quantity) if self.quantity is not None else "",
            "price": str(self.price) if self.price is not None else "",
            "amount": str(self.amount) if self.amount is not None else "",
            "tax_rate": self.tax_rate,
            "tax": str(self.tax_amount) if self.tax_amount is not None else "" # 前端用的是 'tax'
        }

