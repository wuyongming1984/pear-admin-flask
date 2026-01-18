import json
import logging
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms.rights import RightsORM
from pear_admin.orms.role import RoleORM
from pear_admin.orms.dictionary import DictionaryORM, DictionaryDetailORM
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Use 'prod' config for server (matches configs.py)
# Map common env names to our config keys
env = os.getenv("FLASK_ENV", "prod")
env_map = {"production": "prod", "development": "dev", "testing": "test"}
env = env_map.get(env, env)  # Convert if needed
app = create_app(env)

DATA_FILE = os.path.join(os.path.dirname(__file__), '../data/system_data.json')

def import_data():
    if not os.path.exists(DATA_FILE):
        logger.error(f"❌ Data file not found: {DATA_FILE}")
        return

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with app.app_context():
        logger.info(f"Importing data to {env} database...")
        
        try:
            # 1. Import Rights (Upsert)
            logger.info("  Syncing Rights (Menus)...")
            for item in data.get('ums_rights', []):
                # Check exist
                obj = RightsORM.query.get(item['id'])
                if obj:
                    # Update fields
                    for k, v in item.items():
                        if hasattr(obj, k):
                            setattr(obj, k, v)
                else:
                    # Insert
                    obj = RightsORM(**item)
                    db.session.add(obj)
            db.session.flush()

            # 2. Import Roles (Upsert)
            logger.info("  Syncing Roles...")
            for item in data.get('ums_role', []):
                obj = RoleORM.query.get(item['id'])
                # Pre-process: RoleORM.json() has 'rights_ids' which we might want to keep or ignore.
                # It also doesn't include relationship fields directly.
                if obj:
                    for k, v in item.items():
                        if k != 'rights_ids' and hasattr(obj, k):
                            setattr(obj, k, v)
                else:
                    obj = RoleORM(**item)
                    db.session.add(obj)
            db.session.flush()

            # 3. Import Role-Rights (Full Replace for consistency)
            logger.info("  Syncing Role-Permissions...")
            # We truncate/delete all role-rights to ensure 1:1 sync with local config
            # This handles "removed permissions" correctly.
            db.session.execute(text("TRUNCATE TABLE ums_role_rights"))
            
            # Re-insert
            role_rights = data.get('ums_role_rights', [])
            if role_rights:
                # Batch insert is faster
                # Assuming simple structure: {'role_id': 1, 'rights_id': 2}
                # Check column names in table. Usually `role_id` and `rights_id` or `permission_id`
                # Let's inspect the table to be sure or use the ORM association if possible. 
                # Raw SQL insert is safest if we know col names.
                # From 'pear_admin/orms/role.py':
                # rights_list = db.relationship("RightsORM", secondary="ums_role_rights", ...)
                # Default sqlalchemy columns for secondary table are generally `ums_role_id` and `rights_orm_id` if not specified?
                # Or `role_id` and `rights_id`?
                # The export script used `row[0]` and `row[1]`.
                # Let's try to deduce from existing data or schema. 
                # `scripts/grant_dictionary_permission.py` might show how it's done. 
                # Wait, to be safe, let's use the ORM to add.
                pass 

            # Re-process using ORM to be safe about column names
            # But we cleared the table. 
            # We can re-build relationships via RoleORM objects.
            # This is slower but safer than guessing column names.
            
            # Group by role_id
            role_map = {}
            for rr in role_rights:
                rid = rr['role_id']
                if rid not in role_map:
                    role_map[rid] = []
                role_map[rid].append(rr['rights_id'])
            
            for role_id, right_ids in role_map.items():
                role = RoleORM.query.get(role_id)
                if role:
                    # Fetch all rights objects
                    rights_objs = RightsORM.query.filter(RightsORM.id.in_(right_ids)).all()
                    role.rights_list = rights_objs
                    db.session.add(role)
            
            db.session.flush()


            # 4. Import Dictionary (Upsert)
            logger.info("  Syncing Dictionaries...")
            for item in data.get('base_dic', []):
                obj = DictionaryORM.query.get(item['id'])
                if obj:
                    for k, v in item.items():
                         # handle datetime string conversion if needed? 
                         # created_time/update_time might be strings in JSON
                         # But SQLAlchemy might handle ISO strings or fail.
                         # Generally better to ignore timestamps or parse them.
                         # Let's skip timestamps for now to avoid complexity, or parse.
                        if k in ['create_time', 'update_time']:
                             continue
                        if hasattr(obj, k):
                            setattr(obj, k, v)
                else:
                    # Clean properites for constructor
                    clean_item = {k: v for k, v in item.items() if k not in ['create_time', 'update_time']}
                    obj = DictionaryORM(**clean_item)
                    db.session.add(obj)
            db.session.flush()

            # 5. Import Dictionary Details
            logger.info("  Syncing Dictionary Details...")
            # For details, maybe delete all for that dictionary first? 
            # Or just upsert. Upsert is safer for IDs.
            for item in data.get('base_dic_detail', []):
                obj = DictionaryDetailORM.query.get(item['id'])
                if obj:
                    for k, v in item.items():
                        if k in ['create_time', 'update_time']:
                             continue
                        if hasattr(obj, k):
                            setattr(obj, k, v)
                else:
                    clean_item = {k: v for k, v in item.items() if k not in ['create_time', 'update_time']}
                    obj = DictionaryDetailORM(**clean_item)
                    db.session.add(obj)

            db.session.commit()
            logger.info("✅ Data import completed successfully.")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Import failed: {e}")
            raise

if __name__ == '__main__':
    import_data()
