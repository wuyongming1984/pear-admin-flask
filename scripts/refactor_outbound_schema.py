import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from sqlalchemy import text

app = create_app('dev')

def refactor_schema():
    with app.app_context():
        # 1. Add inventory_id column
        try:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE material_outbound ADD COLUMN inventory_id INTEGER REFERENCES material_inventory(id)"))
                conn.commit()
                print("Added inventory_id column.")
        except Exception as e:
            print(f"Error adding inventory_id (might exist): {e}")

        # 2. Drop redundant columns
        columns_to_drop = [
            "project_id",
            "material_name",
            "material_spec",
            "material_unit",
            "outbound_quantity",
            "recipient",
            "seller_price",
            "seller_quantity",
            "seller_id"
        ]
        
        with db.engine.connect() as conn:
            for col in columns_to_drop:
                try:
                    conn.execute(text(f"ALTER TABLE material_outbound DROP COLUMN {col}"))
                    conn.commit()
                    print(f"Dropped column {col}.")
                except Exception as e:
                    print(f"Error dropping {col}: {e}")
                    
        print("Schema refactor complete.")

if __name__ == "__main__":
    refactor_schema()
