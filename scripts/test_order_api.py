import sys
import os
sys.path.append(os.getcwd())
from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import OrderORM

app = create_app()
with app.app_context():
    try:
        order = OrderORM.query.first()
        if not order:
            print("No orders found.")
        else:
            print("Found order:", order.id)
            data = order.json()
            print("JSON serialization successful.")
            print("Data keys:", data.keys())
    except Exception as e:
        print("Error:", e)
        import traceback
        traceback.print_exc()
