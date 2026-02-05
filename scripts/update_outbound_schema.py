import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db
from sqlalchemy import text

app = create_app('dev')

def update_schema():
    with app.app_context():
        print("Checking material_outbound schema...")
        
        # Add material_unit
        try:
            db.session.execute(text("ALTER TABLE material_outbound ADD COLUMN material_unit VARCHAR(32)"))
            print("Added material_unit column")
        except Exception as e:
            print(f"material_unit might already exist: {e}")

        # Add seller_price
        try:
            db.session.execute(text("ALTER TABLE material_outbound ADD COLUMN seller_price NUMERIC(18, 2) DEFAULT 0"))
            print("Added seller_price column")
        except Exception as e:
            print(f"seller_price might already exist: {e}")

        # Add seller_quantity
        try:
            db.session.execute(text("ALTER TABLE material_outbound ADD COLUMN seller_quantity NUMERIC(18, 2) DEFAULT 0"))
            print("Added seller_quantity column")
        except Exception as e:
            print(f"seller_quantity might already exist: {e}")

        # Add seller_id
        try:
            db.session.execute(text("ALTER TABLE material_outbound ADD COLUMN seller_id INTEGER"))
            print("Added seller_id column")
        except Exception as e:
            print(f"seller_id might already exist: {e}")
            
        db.session.commit()
        print("Schema update completed.")

if __name__ == "__main__":
    update_schema()
