
import sys
import os
import json
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import OrderORM
from pear_admin.oss_utils import OSSUtils
import oss2

app = create_app()

def check_oss_status():
    oss_utils = OSSUtils(app)
    if not oss_utils.bucket:
        print("OSS not configured! Aborting.")
        return
        
    bucket = oss_utils.bucket
    
    print("--- Listing files in 'invoices/2025/' ---")
    try:
        for obj in oss2.ObjectIterator(bucket, prefix='invoices/2025/'):
            print(f"File: {obj.key}")
    except Exception as e:
        print(f"Error listing invoices/2025/: {e}")

    print("\n--- Listing files in root (limit 50) ---")
    try:
        count = 0
        for obj in oss2.ObjectIterator(bucket, delimiter='/'):
            if obj.key.endswith('/'): # Skip folders
                continue
            print(f"File: {obj.key}")
            count += 1
            if count >= 50:
                print("... (limit reached)")
                break
    except Exception as e:
        print(f"Error listing root: {e}")

    print("\n--- Checking Order Attachments in DB ---")
    with app.app_context():
        orders = OrderORM.query.filter(OrderORM.attachments.isnot(None)).all()
        unmoved_count = 0
        
        for order in orders:
            try:
                if not order.attachments:
                    continue
                
                attachments = []
                if isinstance(order.attachments, str):
                    try:
                        attachments = json.loads(order.attachments)
                    except:
                        pass
                else:
                    attachments = order.attachments
                    
                if not isinstance(attachments, list):
                    continue
                    
                for att in attachments:
                    if isinstance(att, dict) and att.get('url'):
                        url = att['url']
                        parsed = urlparse(url)
                        key = parsed.path.lstrip('/')
                        
                        if not key.startswith('order_attachments/'):
                            print(f"Order {order.order_number} (ID: {order.id}) has unmoved attachment: {key}")
                            unmoved_count += 1
            except Exception as e:
                print(f"Error checking order {order.id}: {e}")

        if unmoved_count == 0:
            print("No unmoved attachments found in DB.")
        else:
            print(f"Found {unmoved_count} unmoved attachments in DB.")

if __name__ == "__main__":
    check_oss_status()
