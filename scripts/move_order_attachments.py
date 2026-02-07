
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

app = create_app()

def move_attachments():
    oss_utils = OSSUtils(app)
    if not oss_utils.bucket:
        print("OSS not configured! Aborting.")
        return
        
    bucket_name = oss_utils.bucket.bucket_name
    
    with app.app_context():
        # Fetch orders with attachments
        orders = OrderORM.query.filter(OrderORM.attachments.isnot(None)).all()
        print(f"Found {len(orders)} orders with attachments.")
        
        updated_count = 0
        error_count = 0
        
        for order in orders:
            try:
                # Parse attachments
                if not order.attachments:
                    continue
                    
                attachments_data = []
                try:
                    if isinstance(order.attachments, str):
                        attachments_data = json.loads(order.attachments)
                    else:
                        attachments_data = order.attachments
                except:
                    print(f"Failed to parse JSON for order {order.id}")
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
                    
                    # Parse URL to get key
                    # URL format: https://bucket.endpoint/key
                    # or with params if signed (but DB usually stores raw url from upload_file)
                    
                    parsed = urlparse(url)
                    current_key = parsed.path.lstrip('/')
                    
                    # Check if already in correct folder
                    if current_key.startswith('order_attachments/'):
                        new_attachments.append(att)
                        continue
                    
                    # Determine new key
                    filename = os.path.basename(current_key)
                    new_key = f"order_attachments/{filename}"
                    
                    print(f"Moving: {current_key} -> {new_key}")
                    
                    try:
                        # Copy object
                        # oss2.Bucket.copy_object(source_bucket_name, source_key, target_key)
                        # Wait, definition is copy_object(source_bucket_name, source_key, target_key)
                        # Calling on self.bucket: self.bucket.copy_object(bucket_name, current_key, new_key)
                        
                        oss_utils.bucket.copy_object(bucket_name, current_key, new_key)
                        
                        # Delete old object
                        oss_utils.bucket.delete_object(current_key)
                        
                        # Update URL in attachment dict
                        # Reconstruct URL with new key
                        # We can just replace the path in the old URL string or rebuild it
                        # Simple rebuild:
                        domain = oss_utils.bucket.endpoint.replace('http://', '').replace('https://', '')
                        new_url = f"https://{bucket_name}.{domain}/{new_key}"
                        
                        att['url'] = new_url
                        modified = True
                        
                    except Exception as e:
                        print(f"  Error moving object: {e}")
                        error_count += 1
                    
                    new_attachments.append(att)
                
                if modified:
                    order.attachments = json.dumps(new_attachments, ensure_ascii=False)
                    updated_count += 1
                    
            except Exception as e:
                print(f"Error processing order {order.id}: {e}")
                error_count += 1
        
        db.session.commit()
        print(f"Move complete. Updated {updated_count} orders. Encountered {error_count} errors.")

if __name__ == "__main__":
    move_attachments()
