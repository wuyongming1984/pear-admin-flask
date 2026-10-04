"""Original bank receipts and their explicit payment-order associations."""
from datetime import datetime
from pear_admin.extensions import db
from ._base import BaseORM


pay_receipt_relation = db.Table(
    'pay_receipt_relation',
    db.Column('receipt_id', db.Integer, db.ForeignKey('payment_receipt.id', ondelete='CASCADE'), primary_key=True),
    db.Column('pay_id', db.Integer, db.ForeignKey('ums_pay.id', ondelete='CASCADE'), primary_key=True),
)


class PaymentReceiptORM(BaseORM):
    __tablename__ = 'payment_receipt'
    id = db.Column(db.Integer, primary_key=True)
    receipt_number = db.Column(db.String(128), nullable=False, default='')
    payment_date = db.Column(db.Date)
    payer_name = db.Column(db.String(255), nullable=False, default='')
    payee_name = db.Column(db.String(255), nullable=False, default='')
    amount = db.Column(db.Numeric(18, 2))
    bank_name = db.Column(db.String(255), nullable=False, default='')
    remarks = db.Column(db.Text, nullable=False, default='')
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.Text, nullable=False)
    file_type = db.Column(db.String(16), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_hash = db.Column(db.String(64), nullable=False, unique=True)
    create_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    payments = db.relationship('PayORM', secondary=pay_receipt_relation,
                               backref='payment_receipts', lazy='selectin')
