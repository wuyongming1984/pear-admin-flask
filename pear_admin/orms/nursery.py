from pear_admin.extensions import db
from ._base import BaseORM
import datetime

class NurseryPlantORM(BaseORM):
    """
    苗圃-库存表
    存储当前苗木的实时库存和成本
    """
    __tablename__ = "nursery_plant"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, comment="苗木名称")
    category = db.Column(db.String(50), comment="分类(苗木/蔬菜/养殖等)")
    spec = db.Column(db.String(100), comment="规格")
    unit = db.Column(db.String(20), comment="单位")
    quantity = db.Column(db.Numeric(10, 2), default=0, comment="当前库存数量")
    price = db.Column(db.Numeric(10, 2), default=0, comment="加权平均成本价")
    location = db.Column(db.String(100), comment="存放位置")
    
    remark = db.Column(db.String(255), comment="备注")
    
    # Timestamp columns
    create_at = db.Column(db.DateTime, default=datetime.datetime.now, comment="创建时间")
    update_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, comment="更新时间")

    def json(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "spec": self.spec,
            "unit": self.unit,
            "quantity": float(self.quantity) if self.quantity else 0,
            "price": float(self.price) if self.price else 0,
            "location": self.location,
            "create_at": self.create_at.strftime("%Y-%m-%d %H:%M:%S") if self.create_at else "",
            "remark": self.remark
        }

class NurseryTransactionORM(BaseORM):
    """
    苗圃-流水表
    记录所有的入库、出库操作
    """
    __tablename__ = "nursery_transaction"

    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(50), nullable=False, index=True, comment="单号")
    type = db.Column(db.String(10), nullable=False, comment="类型: in/out")
    
    # 关联库存ID (如果是 '非库存商品' 出库，此字段可能为空)
    plant_id = db.Column(db.Integer, comment="关联库存ID")
    
    plant_name = db.Column(db.String(100), comment="苗木名称(快照)")
    spec = db.Column(db.String(100), comment="规格(快照)")
    unit = db.Column(db.String(20), comment="单位(快照)")
    
    quantity = db.Column(db.Numeric(10, 2), nullable=False, comment="变动数量")
    price = db.Column(db.Numeric(10, 2), comment="单价(入库为进价，出库为售价)")
    total_price = db.Column(db.Numeric(12, 2), comment="总价")
    
    operator = db.Column(db.String(50), comment="操作人")
    destination = db.Column(db.String(100), comment="去向/来源")
    location = db.Column(db.String(100), comment="仓库位置")
    
    remark = db.Column(db.String(255), comment="备注")
    
    # Timestamp column
    create_at = db.Column(db.DateTime, default=datetime.datetime.now, comment="创建时间")

    def json(self):
        return {
            "id": self.id,
            "order_no": self.order_no,
            "type": self.type,
            "plant_name": self.plant_name,
            "spec": self.spec,
            "unit": self.unit,
            "quantity": float(self.quantity) if self.quantity else 0,
            "price": float(self.price) if self.price else 0,
            "total_price": float(self.total_price) if self.total_price else 0,
            "operator": self.operator,
            "destination": self.destination,
            "create_at": self.create_at.strftime("%Y-%m-%d %H:%M:%S") if self.create_at else "",
            "remark": self.remark
        }
