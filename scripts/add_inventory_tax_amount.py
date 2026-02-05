import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db
from sqlalchemy import text

app = create_app('dev')

def add_column():
    with app.app_context():
        print("Adding tax_amount to material_inventory...")
        try:
            db.session.execute(text("ALTER TABLE material_inventory ADD COLUMN tax_amount NUMERIC(18, 2) DEFAULT 0"))
            print("Added tax_amount.")
        except Exception as e:
            print(f"Failed to add tax_amount: {e}")
            
        db.session.commit()

if __name__ == "__main__":
    add_column()
