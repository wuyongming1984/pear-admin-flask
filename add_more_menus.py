import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import RightsORM, RoleORM

config_name = os.getenv('FLASK_CONFIG', 'dev')
app = create_app(config_name)

def add_more_menus():
    """添加操作日志和基础数据菜单"""
    with app.app_context():
        parent = RightsORM.query.filter_by(code="nursery:main").first()
        if not parent:
            print("Error: Parent menu not found!")
            return
        
        parent_id = parent.id
        
        menus = [
            {"name": "操作日志", "code": "nursery:logs", "url": "/nursery/logs", "icon": "layui-icon-log", "sort": 5},
            {"name": "基础数据", "code": "nursery:settings", "url": "/nursery/settings", "icon": "layui-icon-set", "sort": 6},
        ]
        
        for menu_data in menus:
            exists = RightsORM.query.filter_by(code=menu_data["code"]).first()
            if exists:
                print(f"Menu '{menu_data['code']}' already exists, skipping.")
                continue
            
            menu = RightsORM(
                name=menu_data["name"],
                code=menu_data["code"],
                type="path",
                url=menu_data["url"],
                icon_sign=menu_data["icon"],
                pid=parent_id,
                sort=menu_data["sort"],
                status=True,
                open_type="_iframe"
            )
            db.session.add(menu)
            print(f"Added: {menu_data['name']}")
        
        db.session.commit()
        
        # Grant to Admin
        admin_role = db.session.get(RoleORM, 1)
        new_rights = RightsORM.query.filter(RightsORM.code.like('nursery%')).all()
        for r in new_rights:
            if r not in admin_role.rights_list:
                admin_role.rights_list.append(r)
        db.session.commit()
        print("Done!")

if __name__ == "__main__":
    add_more_menus()
