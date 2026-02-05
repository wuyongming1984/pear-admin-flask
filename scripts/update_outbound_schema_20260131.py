import sqlite3
import os

def update_schema():
    db_path = r"d:\pear_admin\pear-admin-flask\instance\pear_admin.db"
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    columns_to_add = [
        ("project_id", "INTEGER"),
        ("material_name", "VARCHAR(128)"),
        ("material_spec", "VARCHAR(128)"),
        ("material_unit", "VARCHAR(32)"),
        ("seller_price", "NUMERIC(18, 2) DEFAULT 0"),
        ("seller_quantity", "NUMERIC(18, 2) DEFAULT 0"),
        ("seller_id", "INTEGER"),
        ("tax_rate", "NUMERIC(10, 4) DEFAULT 0")
    ]

    # Get existing columns
    cursor.execute("PRAGMA table_info(material_outbound)")
    existing_cols = [row[1] for row in cursor.fetchall()]

    for col_name, col_type in columns_to_add:
        if col_name not in existing_cols:
            print(f"Adding column {col_name} to material_outbound...")
            try:
                cursor.execute(f"ALTER TABLE material_outbound ADD COLUMN {col_name} {col_type}")
                print(f"Successfully added {col_name}")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
        else:
            print(f"Column {col_name} already exists.")

    conn.commit()
    conn.close()
    print("Database schema update completed.")

if __name__ == "__main__":
    update_schema()
