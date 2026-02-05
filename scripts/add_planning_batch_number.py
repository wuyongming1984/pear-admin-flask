import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db
from sqlalchemy import text

app = create_app('dev')

def add_column():
    with app.app_context():
        print("Adding batch_number to material_planning...")
        try:
            db.session.execute(text("ALTER TABLE material_planning ADD COLUMN batch_number VARCHAR(64)"))
            db.session.commit()
            print("Successfully added batch_number column.")
        except Exception as e:
            print(f"Failed to add column (might already exist): {e}")

if __name__ == "__main__":
    add_column()
