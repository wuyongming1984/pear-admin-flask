from datetime import datetime
from pear_admin.extensions import db


def format_datetime(dt_field):
    """格式化日期时间字段，兼容 SQLite 和 MySQL"""
    if dt_field is None:
        return None
    if isinstance(dt_field, bytes):
        # MySQL 有时返回 bytes 类型
        return dt_field.decode('utf-8')
    elif hasattr(dt_field, 'strftime'):
        return dt_field.strftime('%Y-%m-%d %H:%M:%S')
    else:
        return str(dt_field)


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
            'create_time': format_datetime(self.create_time),
            'update_time': format_datetime(self.update_time)
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
            'create_time': format_datetime(self.create_time),
            'update_time': format_datetime(self.update_time)
        }

