"""
Add access_token column to ums_supplier table
"""
import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    with db.engine.connect() as conn:
        try:
            # Check if column exists first to facilitate re-runs
            # SQLite specific info check, adjust if MySQL is strict
            # For MySQL, 'ADD COLUMN IF NOT EXISTS' is not standard in older versions, 
            # so we just try/catch or assume it's needed.
            print("Attempting to add access_token column to ums_supplier...")
            
            # Using straight SQL for compatibility
            # Note: SQLite doesn't support adding UNIQUE/INDEX in the ADD COLUMN statement easily in one go usually,
            # but standard SQL does. Let's try standard ADD COLUMN first.
            conn.execute(text("ALTER TABLE ums_supplier ADD COLUMN access_token VARCHAR(64) NULL"))
            
            # Add Unique Index separately just to be safe and compatible
            conn.execute(text("CREATE UNIQUE INDEX idx_ums_supplier_access_token ON ums_supplier (access_token)"))
            
            conn.commit()
            print("✓ Successfully added access_token column and index")
        except Exception as e:
            print(f"! Operation may have failed or column already exists: {e}")

