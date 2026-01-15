import sys
import os
import logging

# Add current directory to path
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from sqlalchemy import text, inspect

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Force import of all ORMs to ensure they are registered with SQLAlchemy
from pear_admin import orms

# Set env to prod to match docker environment if not set
if not os.getenv("FLASK_ENV"):
    os.environ["FLASK_ENV"] = "prod"

app = create_app()

def table_exists(table_name, connection):
    inspector = inspect(connection)
    return table_exists_in_inspector(inspector, table_name)

def table_exists_in_inspector(inspector, table_name):
    return table_name in inspector.get_table_names()

def column_exists(table_name, column_name, connection):
    inspector = inspect(connection)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def migrate():
    logger.info("Starting database schema update...")
    with app.app_context():
        # Log which DB we are connecting to
        logger.info(f"Connecting to database: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
        
        # Get connection
        conn = db.engine.connect()
        try:
            inspector = inspect(conn)
            
            # 1. Create ums_payer table (and any other missing tables)
            # db.create_all() will create any tables defined in models that do not exist in DB
            logger.info("Running db.create_all() to create missing tables (e.g. ums_payer)...")
            db.create_all()
            
            if table_exists_in_inspector(inspector, 'ums_payer'):
                logger.info("✅ Table 'ums_payer' checked/created.")
            else:
                logger.error("❌ Failed to create 'ums_payer' table.")

            # 2. Add 'supplier_contact_person' to 'ums_order'
            if table_exists_in_inspector(inspector, 'ums_order'):
                if column_exists('ums_order', 'supplier_contact_person', conn):
                    logger.info("✅ Column 'ums_order.supplier_contact_person' already exists.")
                else:
                    logger.info("Adding column 'supplier_contact_person' to 'ums_order'...")
                    try:
                        # SQLite and MySQL both support ADD COLUMN syntax
                        conn.execute(text("ALTER TABLE ums_order ADD COLUMN supplier_contact_person VARCHAR(64)"))
                        conn.commit()
                        logger.info("✅ Successfully added 'supplier_contact_person' column.")
                    except Exception as e:
                        logger.error(f"❌ Failed to add column: {e}")
            else:
                logger.error("❌ Table 'ums_order' does not exist! Something is very wrong.")

            # 3. Add 'pay_number' unique index if missing (just in case, based on previous context)
            # Skipping complex index checks for now to avoid specific DB dialect issues, assuming Create Table handled it for new tables.
            
            logger.info("Database schema update completed.")
            
        except Exception as e:
            logger.error(f"Migration failed with error: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    migrate()
