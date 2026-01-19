import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import RightsORM, RoleORM

# Allow setting config via env var or default to dev
config_name = os.getenv('FLASK_CONFIG', 'dev')
app = create_app(config_name)

def add_menu():
    with app.app_context():
        # Check if menu already exists
        exists = RightsORM.query.filter_by(code="nursery:main").first()
        
        if exists:
            print("Menu 'nursery:main' already exists. Skipping creation.")
        else:
            # 1. Add Top Level Menu "Nursery Management"
            menu = RightsORM(
                name="苗圃管理",
                code="nursery:main",
                type="menu",
                url="",
                icon_sign="layui-icon-tree", 
                pid=0,
                sort=5,
                status=True,
                open_type="_iframe"
            )
            db.session.add(menu)
            db.session.flush()
            
            parent_id = menu.id
            
            # 2. Add Sub Menu "Inventory"
            sub_menu = RightsORM(
                name="苗木库存",
                code="nursery:inventory",
                type="menu",
                url="/nursery/inventory",
                icon_sign="layui-icon-list",
                pid=parent_id,
                sort=0,
                status=True,
                open_type="_iframe"
            )
            db.session.add(sub_menu)
            
            db.session.commit()
            print(f"Successfully added Nursery menus with Parent ID: {parent_id}")

        # 3. Grant to Admin Role (ID 1)
        admin_role = RoleORM.query.get(1)
             
        # Re-fetch new rights
        new_rights = RightsORM.query.filter(RightsORM.code.like('nursery%')).all()
        for r in new_rights:
            # Check if admin already has it
            if r not in admin_role.rights_list:
                admin_role.rights_list.append(r)
        
        db.session.commit()
        print("Granted permissions to Admin role.")

if __name__ == "__main__":
    add_menu()
