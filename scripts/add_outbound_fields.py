import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pear_admin.extensions import db
from pear_admin import create_app
from sqlalchemy import text

def migrate():
    app = create_app()
    with app.app_context():
        try:
            print("Adding material_name and tax_rate to material_outbound table...")
            
            # Use raw SQL to add columns safely if they don't exist
            # Note: SQLite doesn't support 'IF NOT EXISTS' in ALTER TABLE directly, 
            # but we can try and catch or check PRAGMA.
            
            # Check if columns exist
            columns_info = db.session.execute(text("PRAGMA table_info(material_outbound)")).fetchall()
            column_names = [info[1] for info in columns_info]
            
            if 'material_name' not in column_names:
                db.session.execute(text("ALTER TABLE material_outbound ADD COLUMN material_name VARCHAR(128)"))
                print("Added material_name column.")
            else:
                print("material_name column already exists.")

            if 'tax_rate' not in column_names:
                db.session.execute(text("ALTER TABLE material_outbound ADD COLUMN tax_rate NUMERIC(10, 4) DEFAULT 0"))
                print("Added tax_rate column.")
            else:
                print("tax_rate column already exists.")
                
            db.session.commit()
            print("Migration completed successfully.")
            
        except Exception as e:
            db.session.rollback()
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
