
import sys
import os
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import PayORM

app = create_app()

def verify_pay_migration():
    print("Verifying Payment Attachment Migration...")
    with app.app_context():
        # Count total payments
        total_pays = PayORM.query.count()
        
        # Count payments with attachments
        pays_with_attachments = 0
        attachment_count = 0
        
        # Check a sample
        sample_pays = []
        
        pays = PayORM.query.all()
        for pay in pays:
            if pay.attachments:
                try:
                    atts = json.loads(pay.attachments) if isinstance(pay.attachments, str) else pay.attachments
                    if atts and isinstance(atts, list) and len(atts) > 0:
                        pays_with_attachments += 1
                        attachment_count += len(atts)
                        if len(sample_pays) < 5:
                            sample_pays.append({
                                "pay_number": pay.pay_number,
                                "attachments": atts
                            })
                except:
                    pass
        
        print(f"Total Payments: {total_pays}")
        print(f"Payments with Attachments: {pays_with_attachments}")
        print(f"Total Attachments Found: {attachment_count}")
        print("-" * 30)
        print("Sample Payments with Attachments:")
        for sp in sample_pays:
            print(f"Pay Number: {sp['pay_number']}")
            for att in sp['attachments']:
                print(f"  - {att.get('name')} ({att.get('url')})")

if __name__ == "__main__":
    verify_pay_migration()
