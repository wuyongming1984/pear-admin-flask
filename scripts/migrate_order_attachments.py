
import os
import sys
import re
import json
import requests
import mimetypes
from datetime import datetime as dt
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import OrderORM
from pear_admin.oss_utils import OSSUtils

app = create_app()

SQL_DUMP_PATH = "d:/pear_admin/pear-admin-flask/sf_db_prod20260206.sql"

def load_source_data():
    print(f"Reading SQL dump from {SQL_DUMP_PATH}...")
    
    orders = {}   # order_number (ddbh) -> fjid_str
    files = {}    # fjid -> {url, name}
    
    with open(SQL_DUMP_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith("INSERT INTO `core_order_info`"):
                # Table structure (mapped by index in VALUES):
                # 0: ddid
                # 1: ddbh (Order Number)
                # ...
                # 11: fjid (Attachment ID)
                
                parts = line.split("VALUES", 1)
                if len(parts) < 2: continue
                
                val_part = parts[1].strip().rstrip(";")
                records = re.findall(r"\(([^)]+)\)", val_part)
                for rec in records:
                    # Smart split to handle commas in quotes
                    vals = [x.strip().strip("'") for x in re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", rec)]
                    
                    if len(vals) >= 12:
                        ddbh = vals[1]
                        fjid = vals[11]
                        
                        if fjid and fjid != 'NULL' and fjid != '' and fjid != '0':
                            orders[ddbh] = fjid
                            
            elif line.startswith("INSERT INTO `core_file_info`"):
                # Same as before
                parts = line.split("VALUES", 1)
                if len(parts) < 2: continue
                val_part = parts[1].strip().rstrip(";")
                records = re.findall(r"\(([^)]+)\)", val_part)
                for rec in records:
                    vals = [x.strip().strip("'") for x in re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", rec)]
                    if len(vals) >= 5:
                        f_id = vals[0]
                        url = vals[1]
                        name = vals[4]
                        files[f_id] = {"url": url, "name": name}

    print(f"Loaded {len(orders)} orders with attachments.")
    print(f"Loaded {len(files)} file records.")
    return orders, files

def download_file(url):
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.content, response.headers.get('Content-Type')
    except Exception as e:
        print(f"Error downloading {url}: {e}")
    return None, None

def migrate():
    source_orders, source_files = load_source_data()
    
    oss_utils = OSSUtils(app)
    if not oss_utils.bucket:
        print("OSS not configured! Aborting.")
        return

    with app.app_context():
        # Get all target orders
        target_orders = OrderORM.query.all()
        print(f"Found {len(target_orders)} orders in target DB.")
        
        updated_count = 0
        
        for order in target_orders:
            if order.order_number in source_orders:
                fjid_str = source_orders[order.order_number]
                fjids = [x.strip() for x in fjid_str.split(',') if x.strip()]
                
                print(f"Processing Order '{order.order_number}' (ID: {order.id}). Found {len(fjids)} source attachments.")
                
                new_attachments_list = []
                
                for fjid in fjids:
                    if fjid in source_files:
                        file_info = source_files[fjid]
                        url = file_info['url']
                        original_name = file_info['name']
                        
                        print(f"  - Downloading {original_name} from {url}...")
                        content, content_type = download_file(url)
                        
                        if content:
                            from io import BytesIO
                            import uuid
                            
                            file_stream = BytesIO(content)
                            if '.' not in original_name:
                                ext = mimetypes.guess_extension(content_type) or '.bin'
                                filename = f"{original_name}{ext}"
                            else:
                                filename = original_name
                            
                            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'bin'
                            internal_filename = f"{uuid.uuid4().hex}.{ext}"
                            
                            class MockFileStorage:
                                def __init__(self, stream, filename, mimetype):
                                    self.stream = stream
                                    self.filename = filename
                                    self.mimetype = mimetype
                                def read(self, size=-1):
                                    return self.stream.read(size)
                                def seek(self, offset, whence=0):
                                    return self.stream.seek(offset, whence)
                                def tell(self):
                                    return self.stream.tell()

                            mock_file = MockFileStorage(file_stream, internal_filename, content_type)
                            
                            try:
                                print(f"    Uploading {internal_filename} to OSS...")
                                oss_url = oss_utils.upload_file(mock_file, internal_filename)
                                
                                if oss_url:
                                    print(f"    Success: {oss_url}")
                                    new_attachments_list.append({
                                        "name": original_name,
                                        "url": oss_url,
                                        "size": len(content)
                                    })
                                else:
                                    print("    Failed to get OSS URL.")
                            except Exception as e:
                                print(f"    Upload failed: {e}")
                        else:
                            print("    Download failed.")
                    else:
                        print(f"  - File ID {fjid} not found.")
                
                if new_attachments_list:
                    current_attachments = []
                    if order.attachments:
                        try:
                            current_attachments = json.loads(order.attachments)
                            if not isinstance(current_attachments, list):
                                current_attachments = []
                        except:
                            current_attachments = []
                    
                    current_attachments.extend(new_attachments_list)
                    order.attachments = json.dumps(current_attachments, ensure_ascii=False)
                    updated_count += 1
            
        db.session.commit()
        print(f"Order migration complete. Updated {updated_count} orders.")

if __name__ == "__main__":
    migrate()
