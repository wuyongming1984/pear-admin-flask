from datetime import datetime
from pear_admin.extensions import db

class DictionaryORM(db.Model):
    __tablename__ = 'base_dic'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='主键id')
    code = db.Column(db.String(20), comment='代码')
    name = db.Column(db.String(100), comment='代码中文描述')
    valid_mark = db.Column(db.String(1), default='Y', comment='有效标记')
    create_user = db.Column(db.Integer, comment='创建人员')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_user = db.Column(db.Integer, comment='更新人员')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # Relationship
    details = db.relationship('DictionaryDetailORM', backref='dictionary', lazy='dynamic', cascade='all, delete-orphan')

    def json(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'valid_mark': self.valid_mark,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None,
            'update_time': self.update_time.strftime('%Y-%m-%d %H:%M:%S') if self.update_time else None
        }

class DictionaryDetailORM(db.Model):
    __tablename__ = 'base_dic_detail'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='主键id')
    dic_id = db.Column(db.Integer, db.ForeignKey('base_dic.id'), comment='base_dic表主键')
    code = db.Column(db.String(20), comment='代码')
    value = db.Column(db.String(100), comment='代码值')
    order_no = db.Column(db.Integer, comment='排序号')
    valid_mark = db.Column(db.String(1), default='Y', comment='有效标记')
    create_user = db.Column(db.Integer, comment='创建人员')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_user = db.Column(db.Integer, comment='更新人员')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    def json(self):
        return {
            'id': self.id,
            'dic_id': self.dic_id,
            'code': self.code,
            'value': self.value,
            'order_no': self.order_no,
            'valid_mark': self.valid_mark,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None,
            'update_time': self.update_time.strftime('%Y-%m-%d %H:%M:%S') if self.update_time else None
        }
