
import sys
import os
import oss2

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.oss_utils import OSSUtils

app = create_app()

TARGET_FILES = [
    "9fa6bd6da4464d4a80c87f4487f846c4.pdf",
    "ba76045151ad4396983b59004074ebd9.pdf",
    "f5ae712eb3334860adc58779b5627ebd.pdf",
    "f60e6e48fcb346e1af3deff2b273b8c8.pdf",
    "7aba7728c9544eafa5ef71067af36570.pdf"
]

def find_missing_files():
    oss_utils = OSSUtils(app)
    if not oss_utils.bucket:
        print("OSS not configured!")
        return
        
    bucket = oss_utils.bucket
    print("Searching for missing files in OSS...")
    
    found_map = {}
    
    # Check root
    print("Checking root...")
    for filename in TARGET_FILES:
        exists = bucket.object_exists(filename)
        if exists:
            print(f"FAILED TO MOVE? Found in root: {filename}")
            found_map[filename] = filename
        else:
            print(f"Not in root: {filename}")
            
    # Check order_attachments
    print("\nChecking order_attachments/...")
    for filename in TARGET_FILES:
        key = f"order_attachments/{filename}"
        exists = bucket.object_exists(key)
        if exists:
            print(f"ALREADY MOVED? Found in order_attachments/: {key}")
            found_map[filename] = key
        else:
            print(f"Not in order_attachments/: {key}")
            
    # Check invoices/2025/ just in case
    print("\nChecking invoices/2025/...")
    for filename in TARGET_FILES:
        key = f"invoices/2025/{filename}"
        exists = bucket.object_exists(key)
        if exists:
            print(f"Found in invoices/2025/: {key}")
            found_map[filename] = key

if __name__ == "__main__":
    find_missing_files()
