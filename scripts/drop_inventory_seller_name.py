import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db
from sqlalchemy import text

app = create_app('dev')

def drop_column():
    with app.app_context():
        print("Dropping seller_name from material_inventory...")
        try:
            # Try direct drop (SQLite 3.35.0+)
            db.session.execute(text("ALTER TABLE material_inventory DROP COLUMN seller_name"))
            db.session.commit()
            print("Successfully dropped seller_name column.")
        except Exception as e:
            print(f"Direct drop failed: {e}")
            print("Attempting table recreation method not implemented (assuming SQLite version is recent enough).")
            # If we really needed table recreation, we would implement it here.
            # But for this environment, let's see if direct drop works first.

if __name__ == "__main__":
    drop_column()
