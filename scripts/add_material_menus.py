import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import RightsORM, RoleORM

app = create_app('dev')

def add_material_menus_func():
    with app.app_context():
        # 1. Create Top Level Menu
        top_code = "material:main"
        top_menu = RightsORM.query.filter_by(code=top_code).first()
        if not top_menu:
            top_menu = RightsORM(
                name="材料流转大师",
                code=top_code,
                type="menu",
                icon_sign="layui-icon-app",
                sort=0,
                status=True
            )
            db.session.add(top_menu)
            db.session.commit()
            print("Created Top Menu: 材料流转大师")
        else:
            print("Top Menu already exists.")
        
        parent_id = top_menu.id
        
        # 2. Sub Menus
        menus = [
            {"name": "控制中心", "code": "material:dashboard", "url": "/view/material/dashboard", "icon": "layui-icon-console"},
            {"name": "发票详情库", "code": "material:invoice", "url": "/view/material/invoice", "icon": "layui-icon-form"},
            {"name": "合同策划", "code": "material:planning", "url": "/view/material/planning", "icon": "layui-icon-list"},
            {"name": "拟入库计划", "code": "material:inbound", "url": "/view/material/inbound", "icon": "layui-icon-cart-simple"},
            {"name": "库存台账(进项)", "code": "material:inventory", "url": "/view/material/inventory", "icon": "layui-icon-template-1"},
            {"name": "拟出库计划", "code": "material:outbound", "url": "/view/material/outbound", "icon": "layui-icon-export"},
            {"name": "出库记录(销项)", "code": "material:outbound_records", "url": "/view/material/outbound_records", "icon": "layui-icon-log"},
            {"name": "AI 智能看板", "code": "material:aidashboard", "url": "/view/material/dashboard", "icon": "layui-icon-chart-screen"},
        ]
        
        for m in menus:
            exists = RightsORM.query.filter_by(code=m['code']).first()
            if not exists:
                new_menu = RightsORM(
                    name=m['name'],
                    code=m['code'],
                    type="menu",
                    url=m['url'],
                    icon_sign=m['icon'],
                    pid=parent_id,
                    sort=0,
                    status=True
                )
                db.session.add(new_menu)
                print(f"Created Sub Menu: {m['name']}")
            else:
                exists.url = m['url']
                exists.open_type = None
                db.session.add(exists)
                print(f"Updated Sub Menu: {m['name']} URL to {m['url']} and cleared open_type")
        
        db.session.commit()
        
        # 3. Grant to Admin (Role ID 1)
        admin_role = db.session.get(RoleORM, 1)
        if admin_role:
            # Grant top menu
            if top_menu not in admin_role.rights_list:
                admin_role.rights_list.append(top_menu)
            
            # Grant sub menus
            sub_menus = RightsORM.query.filter(RightsORM.pid == top_menu.id).all()
            for sm in sub_menus:
                 if sm not in admin_role.rights_list:
                    admin_role.rights_list.append(sm)
            
            db.session.commit()
            print("Granted permissions to Admin.")

if __name__ == "__main__":
    add_material_menus_func()
