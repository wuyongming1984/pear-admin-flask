import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import RightsORM

app = create_app()

with app.app_context():
    print("正在测试新增权限...")
    try:
        # 模拟前端数据
        data = {
            "name": "测试权限",
            "type": "menu",
            "icon_sign": "layui-icon-engine",
            "sort": 1,
            "open_type": "_component",
            "pid": 0, # 测试 pid=0
            "status": True
        }
        
        # 尝试通过 ORM 插入
        right = RightsORM(**data)
        right.save()
        print(f"✅ 新增成功，ID: {right.id}")
        
        # 清理测试数据
        # db.session.delete(right)
        # db.session.commit()
    except Exception as e:
        print(f"❌ 新增失败: {e}")
        import traceback
        traceback.print_exc()
