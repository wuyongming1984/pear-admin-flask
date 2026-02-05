import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import MaterialInventoryORM, SupplierORM
from sqlalchemy import text

app = create_app('dev')

def update_schema():
    with app.app_context():
        print("Checking material_inventory schema...")
        
        # 1. Add seller_id column
        try:
            db.session.execute(text("ALTER TABLE material_inventory ADD COLUMN seller_id INTEGER"))
            print("Added seller_id column")
        except Exception as e:
            print(f"seller_id might already exist: {e}")
            
        db.session.commit()

        # 2. Migrate data
        print("Migrating data from seller_name to seller_id...")
        inventories = MaterialInventoryORM.query.all()
        count = 0
        new_suppliers = 0
        
        for inv in inventories:
            # We access seller_name via raw connection or if we didn't remove it from model.
            # Since model removed/deprecated it but mapped it, we might not be able to access it via ORM if mapped to same column?
            # Wait, I mapped `seller_id` to `seller_id` column.
            # `seller_name` column still exists in DB but is not in ORM? 
            # I commented it out in ORM code? No, I just removed the line.
            # So I need to use SQL to get the old value.
            
            # Actually, let's use SQL to fetch everything and update via SQL or ORM.
            
            try:
                # Fetch raw (id, seller_name)
                result = db.session.execute(text(f"SELECT id, seller_name FROM material_inventory WHERE id = {inv.id}")).fetchone()
                if not result: continue
                
                raw_seller_name = result[1]
                
                if raw_seller_name:
                    # Find supplier by name
                    supplier = SupplierORM.query.filter_by(name=raw_seller_name).first()
                    if not supplier:
                        # Create new supplier
                        supplier = SupplierORM(name=raw_seller_name, type_id=1, remark="Auto-created from inventory migration")
                        db.session.add(supplier)
                        db.session.flush() # Get ID
                        new_suppliers += 1
                        print(f"Created new supplier: {raw_seller_name}")
                        
                    inv.seller_id = supplier.id
                    count += 1
            except Exception as e:
                print(f"Error migrating row {inv.id}: {e}")

        db.session.commit()
        print(f"Migration completed. Updated {count} records, Created {new_suppliers} new suppliers.")

if __name__ == "__main__":
    update_schema()
