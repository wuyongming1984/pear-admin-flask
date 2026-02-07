
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

def analyze_root_files():
    oss_utils = OSSUtils(app)
    if not oss_utils.bucket:
        print("OSS not configured!")
        return
        
    bucket = oss_utils.bucket
    
    # 1. Build map of known files from DB
    order_files = set()
    project_files = set()
    
    with app.app_context():
        print("Loading DB records...")
        
        # Orders
        orders = OrderORM.query.filter(OrderORM.attachments.isnot(None)).all()
        for o in orders:
            try:
                atts = []
                if isinstance(o.attachments, str):
                    try:
                        atts = json.loads(o.attachments)
                    except: pass
                else:
                    atts = o.attachments
                
                if isinstance(atts, list):
                    for att in atts:
                        if isinstance(att, dict) and att.get('url'):
                            path = urlparse(att['url']).path.lstrip('/')
                            filename = os.path.basename(path)
                            order_files.add(filename) # Store filename to match root files
            except: pass
            
        # Projects
        projects = ProjectORM.query.filter(ProjectORM.attachments.isnot(None)).all()
        for p in projects:
            try:
                atts = []
                if isinstance(p.attachments, str):
                    try:
                        atts = json.loads(p.attachments)
                    except: pass
                else:
                    atts = p.attachments
                    
                if isinstance(atts, list):
                    for att in atts:
                        if isinstance(att, dict) and att.get('url'):
                            path = urlparse(att['url']).path.lstrip('/')
                            filename = os.path.basename(path)
                            project_files.add(filename)
            except: pass
            
    print(f"Known Order Files: {len(order_files)}")
    print(f"Known Project Files: {len(project_files)}")
    
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
    
    # 3. Analyze
    belong_to_order = []
    belong_to_project = []
    orphaned = []
    
    for f in root_files:
        if f in order_files:
            belong_to_order.append(f)
        elif f in project_files:
            belong_to_project.append(f)
        else:
            orphaned.append(f)
            
    print("\n--- Analysis Result ---")
    print(f"Files belonging to Orders (Should have been moved): {len(belong_to_order)}")
    for f in belong_to_order:
        print(f"  [ORDER] {f}")
        
    print(f"\nFiles belonging to Projects (Expected in root): {len(belong_to_project)}")
    # for f in belong_to_project:
    #     print(f"  [PROJECT] {f}")
        
    print(f"\nOrphaned/Unknown Files: {len(orphaned)}")
    for f in orphaned:
        print(f"  [???] {f}")

if __name__ == "__main__":
    analyze_root_files()
