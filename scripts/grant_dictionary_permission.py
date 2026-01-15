import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import RightsORM, RoleORM, UserORM

app = create_app()

with app.app_context():
    print("正在为管理员角色添加字典管理权限...")
    try:
        # 找到字典管理菜单
        dictionary_menu = RightsORM.query.filter_by(name="字典管理").first()
        if not dictionary_menu:
            print("❌ 未找到字典管理菜单")
            exit(1)
        
        print(f"✓ 找到字典管理菜单，ID: {dictionary_menu.id}")
        
        # 找到管理员角色（通常是第一个角色或名为"管理员"的角色）
        admin_role = RoleORM.query.filter_by(name="管理员").first()
        if not admin_role:
            # 尝试找id=1的角色
            admin_role = RoleORM.query.get(1)
        
        if not admin_role:
            print("❌ 未找到管理员角色")
            exit(1)
            
        print(f"✓ 找到管理员角色: {admin_role.name} (ID: {admin_role.id})")
        
        # 检查是否已经有该权限
        if dictionary_menu in admin_role.rights_list:
            print("⚠️  管理员角色已拥有字典管理权限")
        else:
            # 添加权限
            admin_role.rights_list.append(dictionary_menu)
            db.session.commit()
            print("✅ 已为管理员角色添加字典管理权限")
        
        # 检查当前用户wym
        user = UserORM.query.filter_by(username="wym").first()
        if user:
            print(f"\n✓ 用户 'wym' 的角色列表:")
            for role in user.role_list:
                print(f"  - {role.name} (ID: {role.id})")
                if dictionary_menu in role.rights_list:
                    print(f"    ✓ 该角色拥有字典管理权限")
        
        print("\n🎉 配置完成！请退出登录后重新登录，或刷新页面查看效果。")
        
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
