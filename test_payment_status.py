import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import PayORM

app = create_app()
with app.app_context():
    # Get first 5 payment records
    pays = db.session.query(PayORM).limit(5).all()
    print("Payment Status Values:")
    print("-" * 50)
    for pay in pays:
        print(f"ID: {pay.id}, Status: '{pay.payment_status}', Type: {type(pay.payment_status)}")
        print(f"  JSON: {pay.json()}")
        print()
