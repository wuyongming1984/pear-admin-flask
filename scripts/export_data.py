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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

app = create_app("dev")  # Use local dev config to export local data

DATA_DIR = os.path.join(os.path.dirname(__file__), '../data')
EXPORT_FILE = os.path.join(DATA_DIR, 'system_data.json')

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def export_data():
    ensure_data_dir()
    
    with app.app_context():
        logger.info("Exporting data to JSON...")

        data = {
            'ums_rights': [],
            'ums_role': [],
            'ums_role_rights': [],
            'base_dic': [],
            'base_dic_detail': []
        }

        # 1. Export Rights (Menus/Permissions)
        rights = RightsORM.query.all()
        for r in rights:
            item = r.json()
            # RightsORM.json() returns 'id', 'pid' etc.
            # We need to ensure we export all fields necessary for reconstruction
             # Let's check RightsORM.json again... it seems complete.
            data['ums_rights'].append(item)
        logger.info(f"  - Rights: {len(data['ums_rights'])}")

        # 2. Export Roles
        roles = RoleORM.query.all()
        for r in roles:
            item = r.json()
            # RoleORM.json() includes 'rights_ids' which is redundant char field, 
            # but we also need to handle the relationship table `ums_role_rights`
            data['ums_role'].append(item)
        logger.info(f"  - Roles: {len(data['ums_role'])}")

        # 3. Export Role-Rights (Many-to-Many)
        # We need to query the association table directly
        # Since it's not a model class, we query the table object
        role_rights_table = RoleORM.rights_list.property.secondary
        results = db.session.query(role_rights_table).all()
        
        # 按列名读取，避免将关联记录的 id 误当成 role_id。
        for row in results:
            data['ums_role_rights'].append({
                'role_id': row._mapping['role_id'],
                'rights_id': row._mapping['rights_id']
            })
        logger.info(f"  - Role-Rights: {len(data['ums_role_rights'])}")

        # 4. Export Dictionary
        dics = DictionaryORM.query.all()
        for d in dics:
            data['base_dic'].append(d.json())
        logger.info(f"  - Dictionaries: {len(data['base_dic'])}")

        # 5. Export Dictionary Details
        details = DictionaryDetailORM.query.all()
        for d in details:
            data['base_dic_detail'].append(d.json())
        logger.info(f"  - Dictionary Details: {len(data['base_dic_detail'])}")

        # Save to file
        with open(EXPORT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n✅ Data exported to: {EXPORT_FILE}")

if __name__ == '__main__':
    export_data()
