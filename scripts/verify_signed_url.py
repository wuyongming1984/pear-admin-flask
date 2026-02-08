
import os
import sys
import json
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.orms import PayORM

load_dotenv()

def verify_signed_url():
    app = create_app("prod")
    
    with app.app_context():
        # Find a payment with attachments
        query = PayORM.query.filter(PayORM.attachments.like('%pay_attachments/%')).limit(1)
        pay = query.first()
        
        if not pay:
            print("No payment with attachments found.")
            return

        print(f"Checking Pay: {pay.pay_number}")
        data = pay.json()
        
        atts = data.get('attachments_list', [])
        if not atts:
            print("No attachments in JSON.")
            return
            
        for att in atts:
            url = att.get('url')
            print(f"Attachment: {att.get('name')}")
            print(f"URL: {url}")
            
            if 'OSSAccessKeyId' in url and 'Expires' in url and 'Signature' in url:
                print("SUCCESS: URL is signed.")
            else:
                print("FAILURE: URL is NOT signed.")

if __name__ == "__main__":
    verify_signed_url()
