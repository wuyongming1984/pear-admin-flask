import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import MaterialOutboundORM, MaterialInventoryORM

app = create_app('dev')

def debug_join():
    with app.app_context():
        print("Testing Outbound Join Inventory Query...")
        try:
            # Simulate the params: status='pending'
            status = 'pending'
            query = MaterialOutboundORM.query.filter_by(status=status)
            
            # Test Join
            # Note: The view uses .join(MaterialOutboundORM.inventory)
            query = query.join(MaterialOutboundORM.inventory)
            
            print(f"Query: {query}")
            
            pagination = query.paginate(page=1, per_page=10, error_out=False)
            
            print(f"Found {len(pagination.items)} items in pagination.")
            
            for item in pagination.items:
                print(f"Processing Item ID: {item.id}...")
                data = item.json()
                print(f"  > Loaded JSON for Item {item.id}. Seller: {data.get('seller_name')}")
                
            print("JOIN Query Test Successful!")
            
        except Exception as e:
            print("!!! JOIN Query Passed FAILED !!!")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_join()
