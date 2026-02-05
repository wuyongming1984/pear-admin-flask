import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from sqlalchemy import text

app = create_app('dev')

def add_invoice_id():
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE material_outbound ADD COLUMN invoice_id INTEGER REFERENCES material_invoice(id)"))
                conn.commit()
                print("Added invoice_id column.")
        except Exception as e:
            print(f"Error adding invoice_id: {e}")

if __name__ == "__main__":
    add_invoice_id()
