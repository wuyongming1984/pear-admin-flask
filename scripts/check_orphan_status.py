
import sys
import os
import oss2

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.oss_utils import OSSUtils

app = create_app()

TARGET_FILE = "09d304eecaae4c17b514aa07914d5b42.pdf"

def check_orphan():
    oss_utils = OSSUtils(app)
    bucket = oss_utils.bucket
    
    print(f"Looking for {TARGET_FILE}...")
    
    # Check root
    if bucket.object_exists(TARGET_FILE):
        print(f"Found in ROOT: {TARGET_FILE}")
    else:
        print(f"Not in ROOT")
        
    # Check order_attachments/orphaned/
    key = f"order_attachments/orphaned/{TARGET_FILE}"
    if bucket.object_exists(key):
        print(f"Found in ORPHANED: {key}")
    else:
        print(f"Not in ORPHANED")
        
    # Check order_attachments/
    key = f"order_attachments/{TARGET_FILE}"
    if bucket.object_exists(key):
        print(f"Found in ORDER_ATTACHMENTS: {key}")
    else:
        print(f"Not in ORDER_ATTACHMENTS")

if __name__ == "__main__":
    check_orphan()
