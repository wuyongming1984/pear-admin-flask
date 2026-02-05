import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db
from sqlalchemy import text

app = create_app('dev')

def add_columns():
    with app.app_context():
        print("Adding tax fields to material_inventory...")
        try:
            db.session.execute(text("ALTER TABLE material_inventory ADD COLUMN tax_rate NUMERIC(10, 4) DEFAULT 0"))
            print("Added tax_rate.")
        except Exception as e:
            print(f"Failed to add tax_rate: {e}")
            
        try:
            db.session.execute(text("ALTER TABLE material_inventory ADD COLUMN price_no_tax NUMERIC(18, 2) DEFAULT 0"))
            print("Added price_no_tax.")
        except Exception as e:
            print(f"Failed to add price_no_tax: {e}")
            
        db.session.commit()

if __name__ == "__main__":
    add_columns()
