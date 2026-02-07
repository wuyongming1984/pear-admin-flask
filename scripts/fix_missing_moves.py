
import sys
import os
import json
from urllib.parse import urlparse
import oss2

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import OrderORM
from pear_admin.oss_utils import OSSUtils

app = create_app()

def fix_moves():
    oss_utils = OSSUtils(app)
    if not oss_utils.bucket:
        print("OSS not configured! Aborting.")
        return
        
    bucket = oss_utils.bucket
    bucket_name = bucket.bucket_name
    
    with app.app_context():
        # Fetch orders with attachments
        orders = OrderORM.query.filter(OrderORM.attachments.isnot(None)).all()
        print(f"Checking {len(orders)} orders...")
        
        updated_count = 0
        
        for order in orders:
            try:
                if not order.attachments:
                    continue
                    
                attachments_data = []
                try:
                    if isinstance(order.attachments, str):
                        attachments_data = json.loads(order.attachments)
                    else:
                        attachments_data = order.attachments
                except:
                    continue
                    
                if not isinstance(attachments_data, list):
                    continue
                
                modified = False
                new_attachments = []
                
                for att in attachments_data:
                    if not isinstance(att, dict) or not att.get('url'):
                        new_attachments.append(att)
                        continue
                        
                    url = att['url']
                    parsed = urlparse(url)
                    current_key = parsed.path.lstrip('/')
                    
                    # Skip if already correct
                    if current_key.startswith('order_attachments/'):
                        new_attachments.append(att)
                        continue
                    
                    # Prepare new key
                    filename = os.path.basename(current_key)
                    new_key = f"order_attachments/{filename}"
                    
                    # 1. Try to find the SOURCE object
                    source_key = current_key
                    if not bucket.object_exists(source_key):
                        print(f"Source not found at {source_key}. Checking invoices/2025/...")
                        alt_key = f"invoices/2025/{filename}"
                        if bucket.object_exists(alt_key):
                            print(f"  Found at {alt_key}")
                            source_key = alt_key
                        else:
                            print(f"  Not found at {alt_key} either. Skipping.")
                            new_attachments.append(att) # Keep original if we can't find it
                            continue
                            
                    print(f"Moving: {source_key} -> {new_key}")
                    
                    try:
                        bucket.copy_object(bucket_name, source_key, new_key)
                        bucket.delete_object(source_key)
                        
                        # Update URL
                        domain = bucket.endpoint.replace('http://', '').replace('https://', '')
                        new_url = f"https://{bucket_name}.{domain}/{new_key}"
                        
                        att['url'] = new_url
                        modified = True
                        
                    except Exception as e:
                        print(f"  Error moving object: {e}")
                    
                    new_attachments.append(att)
                
                if modified:
                    order.attachments = json.dumps(new_attachments, ensure_ascii=False)
                    updated_count += 1
                    
            except Exception as e:
                print(f"Error processing order {order.id}: {e}")
        
        if updated_count > 0:
            db.session.commit()
            print(f"Fix complete. Updated {updated_count} orders.")
        else:
            print("No updates needed.")

if __name__ == "__main__":
    fix_moves()
