import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import RightsORM, RoleORM

config_name = os.getenv('FLASK_CONFIG', 'dev')
app = create_app(config_name)

def add_nursery_menus():
    """添加苗圃管理完整菜单结构"""
    with app.app_context():
        # 查找现有父菜单
        parent = RightsORM.query.filter_by(code="nursery:main").first()
        if not parent:
            print("Error: Parent menu 'nursery:main' not found!")
            return
        
        parent_id = parent.id
        print(f"Found parent menu ID: {parent_id}")
        
        # 定义新菜单项
        menus = [
            {"name": "仪表盘", "code": "nursery:dashboard", "url": "/nursery/dashboard", "icon": "layui-icon-chart", "sort": 0},
            {"name": "库存明细", "code": "nursery:inventory", "url": "/nursery/inventory", "icon": "layui-icon-list", "sort": 1},
            {"name": "入库登记", "code": "nursery:inbound", "url": "/nursery/inbound", "icon": "layui-icon-addition", "sort": 2},
            {"name": "出库管理", "code": "nursery:outbound", "url": "/nursery/outbound", "icon": "layui-icon-export", "sort": 3},
            {"name": "出库单管理", "code": "nursery:orders", "url": "/nursery/orders", "icon": "layui-icon-file", "sort": 4},
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
            print(f"Added menu: {menu_data['name']}")
        
        db.session.commit()
        
        # Grant to Admin Role
        admin_role = RoleORM.query.get(1)
        new_rights = RightsORM.query.filter(RightsORM.code.like('nursery%')).all()
        for r in new_rights:
            if r not in admin_role.rights_list:
                admin_role.rights_list.append(r)
        
        db.session.commit()
        print("Granted all nursery permissions to Admin role.")

if __name__ == "__main__":
    add_nursery_menus()
