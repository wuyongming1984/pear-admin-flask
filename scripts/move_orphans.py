
import sys
import os
import json
from urllib.parse import urlparse
import oss2

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import OrderORM, ProjectORM
from pear_admin.oss_utils import OSSUtils

app = create_app()

def move_orphans():
    oss_utils = OSSUtils(app)
    if not oss_utils.bucket:
        print("OSS not configured!")
        return
        
    bucket = oss_utils.bucket
    bucket_name = bucket.bucket_name
    
    # 1. Build map of known files from DB
    known_files = set()
    
    with app.app_context():
        print("Loading DB records to identify known files...")
        
        # Orders
        orders = OrderORM.query.filter(OrderORM.attachments.isnot(None)).all()
        for o in orders:
            try:
                atts = []
                if isinstance(o.attachments, str):
                    try: atts = json.loads(o.attachments)
                    except: pass
                else:
                    atts = o.attachments
                
                if isinstance(atts, list):
                    for att in atts:
                        if isinstance(att, dict) and att.get('url'):
                            path = urlparse(att['url']).path.lstrip('/')
                            filename = os.path.basename(path)
                            known_files.add(filename)
            except: pass
            
        # Projects
        projects = ProjectORM.query.filter(ProjectORM.attachments.isnot(None)).all()
        for p in projects:
            try:
                atts = []
                if isinstance(p.attachments, str):
                    try: atts = json.loads(p.attachments)
                    except: pass
                else:
                    atts = p.attachments
                    
                if isinstance(atts, list):
                    for att in atts:
                        if isinstance(att, dict) and att.get('url'):
                            path = urlparse(att['url']).path.lstrip('/')
                            filename = os.path.basename(path)
                            known_files.add(filename)
            except: pass
            
    print(f"Total known files in DB: {len(known_files)}")
    
    # 2. List root files
    print("\nListing root files in OSS...")
    root_files = []
    try:
        for obj in oss2.ObjectIterator(bucket, delimiter='/'):
            if obj.key.endswith('/'): 
                continue
            root_files.append(obj.key)
    except Exception as e:
        print(f"Error listing oss: {e}")
        return

    print(f"Found {len(root_files)} files in root.")
    
    # 3. Identify and Move Orphans
    moved_count = 0
    
    print("\nProcessing orphans...")
    for f in root_files:
        if f in known_files:
            # It's a known file (likely a Project attachment), skip it
            # print(f"Skipping known file: {f}")
            continue
            
        # It's an orphan
        new_key = f"order_attachments/orphaned/{f}"
        print(f"Moving orphan: {f} -> {new_key}")
        
        try:
            bucket.copy_object(bucket_name, f, new_key)
            bucket.delete_object(f)
            moved_count += 1
        except Exception as e:
            print(f"  Error moving {f}: {e}")

    print(f"\nMove complete. Moved {moved_count} orphans.")

if __name__ == "__main__":
    move_orphans()
