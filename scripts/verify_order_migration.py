
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import OrderORM
import json

app = create_app()

def verify():
    with app.app_context():
        # Find orders with attachments
        orders_with_attachments = OrderORM.query.filter(OrderORM.attachments.isnot(None)).all()
        print(f"Orders with updated attachments: {len(orders_with_attachments)}")
        
        if len(orders_with_attachments) > 0:
            # Check a few
            for i in range(min(5, len(orders_with_attachments))):
                o = orders_with_attachments[i]
                print(f"Order: {o.order_number}")
                print(f"  Attachments: {o.attachments}")
                
if __name__ == "__main__":
    verify()
