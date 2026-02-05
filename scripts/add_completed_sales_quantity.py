from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db

app = create_app()

from sqlalchemy import text, inspect

def add_column():
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('material_outbound')]
            
            if 'completed_sales_quantity' in columns:
                print("Column 'completed_sales_quantity' already exists.")
                return

            print("Adding column 'completed_sales_quantity'...")
            with db.engine.connect() as conn:
                # SQLite and MySQL both support ADD COLUMN syntax for simple types (though SQLite has limitations, this simple add is fine)
                # Note: SQLite ignores comments in ALTER TABLE, MySQL uses them. We'll strip comment for max compatibility or just use a simple statement.
                # Simplest compatible SQL:
                conn.execute(text("ALTER TABLE material_outbound ADD COLUMN completed_sales_quantity DECIMAL(18, 2) DEFAULT 0"))
                conn.commit()
            print("Column added successfully.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    add_column()
