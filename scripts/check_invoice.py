from pear_admin import create_app
from pear_admin.orms.material import MaterialInvoiceORM

app = create_app("dev")
# app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///pear_admin.db" # Default for dev
import os
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
db_path = os.path.join(basedir, 'pear_admin.db')
print(f"Checking DB at: {db_path}")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path

with app.app_context():
    print(f"App Config URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    if os.path.exists(db_path):
        print(f"DB File Size: {os.path.getsize(db_path)} bytes")
    invoices = MaterialInvoiceORM.query.order_by(MaterialInvoiceORM.id.desc()).limit(5).all()
    print(f"Found {len(invoices)} invoices.")
    for inv in invoices:
        print(f"ID: {inv.id}, Num: {inv.invoice_number}, Status: {inv.ocr_status}, Err: {inv.ocr_error}, Path: {inv.file_path}, Time: {inv.create_at}")
        print(f"ID: {invoice.id}")
        print(f"File: {invoice.file_name}")
        print(f"Status: {invoice.ocr_status}")
        print(f"Error: {invoice.ocr_error}")
        print(f"Result len: {len(invoice.ocr_result) if invoice.ocr_result else 0}")
    else:
        print("No invoice found")
