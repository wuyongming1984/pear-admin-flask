import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import RightsORM

app = create_app()

with app.app_context():
    print("正在检查并修复字典管理菜单...")
    try:
        # 查找字典管理菜单
        dictionary_menu = RightsORM.query.filter_by(name="字典管理").first()
        
        if dictionary_menu:
            print(f"找到字典管理菜单，ID: {dictionary_menu.id}")
            print(f"  当前URL: {dictionary_menu.url}")
            print(f"  当前icon: {dictionary_menu.icon_sign}")
            print(f"  当前open_type: {dictionary_menu.open_type}")
            
            # 更新配置，确保路径正确
            dictionary_menu.url = "/system/dictionary/"
            dictionary_menu.open_type = "_component"
            dictionary_menu.icon_sign = "layui-icon-template"
            
            db.session.commit()
            print("✅ 菜单配置已更新")
            print(f"  新URL: {dictionary_menu.url}")
        else:
            print("❌ 未找到字典管理菜单")
            
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
