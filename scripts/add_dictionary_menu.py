import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import RightsORM

app = create_app()

with app.app_context():
    print("正在添加字典管理菜单...")
    try:
        # 先查找"系统管理"菜单的ID (作为父级菜单)
        system_menu = RightsORM.query.filter_by(name="系统管理", type="menu").first()
        if not system_menu:
            print("未找到'系统管理'菜单，将作为顶级菜单添加")
            parent_id = 0
        else:
            parent_id = system_menu.id
            print(f"找到父级菜单'系统管理'，ID: {parent_id}")
        
        # 检查是否已存在字典管理菜单
        existing = RightsORM.query.filter_by(name="字典管理").first()
        if existing:
            print(f"⚠️  '字典管理'菜单已存在，ID: {existing.id}")
            print(f"   URL: {existing.url}")
            print(f"   父级ID: {existing.pid}")
        else:
            # 添加字典管理菜单
            dictionary_menu = RightsORM(
                name="字典管理",
                code="dictionary:main",
                type="menu",
                url="/system/dictionary/",
                icon_sign="layui-icon-template",
                status=True,
                sort=90,  # 排序号，可根据需要调整
                open_type="_component",
                pid=parent_id
            )
            db.session.add(dictionary_menu)
            db.session.commit()
            print(f"✅ '字典管理'菜单添加成功！")
            print(f"   ID: {dictionary_menu.id}")
            print(f"   URL: {dictionary_menu.url}")
            print(f"   父级ID: {dictionary_menu.pid}")
            
    except Exception as e:
        print(f"❌ 添加失败: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
