import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import MaterialOutboundORM

app = create_app('dev')

def debug():
    with app.app_context():
        print("Querying MaterialOutboundORM...")
        try:
            items = MaterialOutboundORM.query.all()
            print(f"Found {len(items)} items.")
            for item in items:
                print(f"Item ID: {item.id}, Status: {item.status}")
                # This is likely where it crashes
                json_data = item.json()
                print("JSON OK")
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug()
