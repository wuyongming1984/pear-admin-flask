
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db, oss
from pear_admin.orms import OrderORM, ProjectORM

app = create_app()

def verify_signed():
    with app.app_context():
        # Check Project Attachment
        print("Checking Project Attachments...")
        project = ProjectORM.query.filter(ProjectORM.attachments.isnot(None)).first()
        if project:
            p_json = project.json()
            # Check attachments_list
            if p_json.get('attachments_list'):
                url = p_json['attachments_list'][0]['url']
                print(f"Project Attachment URL: {url}")
                if 'Signature=' in url or 'Expires=' in url or 'OSSAccessKeyId=' in url:
                    print("SUCCESS: Project URL is signed.")
                else:
                    print("WARNING: Project URL might NOT be signed (or bucket is public).")
            else:
                print("Project has no attachments_list.")
        else:
            print("No project with attachments found.")

        # Check Order Attachment
        print("\nChecking Order Attachments...")
        order = OrderORM.query.filter(OrderORM.attachments.isnot(None)).first()
        if order:
            o_json = order.json()
            # Check attachments_list (parsed from json)
            if o_json.get('attachments_list'):
                url = o_json['attachments_list'][0]['url']
                print(f"Order Attachment URL: {url}")
                if 'Signature=' in url or 'Expires=' in url or 'OSSAccessKeyId=' in url:
                    print("SUCCESS: Order URL is signed.")
                else:
                    print("WARNING: Order URL might NOT be signed.")
            else:
                print("Order has no attachments_list.")
        else:
            print("No order with attachments found.")

if __name__ == "__main__":
    verify_signed()
