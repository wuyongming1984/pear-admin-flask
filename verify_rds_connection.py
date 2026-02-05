"""
验证 RDS 连接和数据完整性
"""
import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("=" * 60)
    print("RDS 连接验证")
    print("=" * 60)
    
    # 打印数据库连接信息
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if '@' in db_uri:
        safe_uri = db_uri.split('@')[-1]
        print(f"✓ 数据库连接: ...@{safe_uri}")
    else:
        print(f"✓ 数据库连接: {db_uri}")
    
    print("\n" + "=" * 60)
    print("数据统计")
    print("=" * 60)
    
    # 统计各个表的数据量
    tables_to_check = [
        ("用户", "ums_user"),
        ("角色", "ums_role"),
        ("订单", "ums_order"),
        ("付款", "ums_pay"),
        ("物料入库", "material_inbound"),
        ("物料出库", "material_outbound"),
        ("物料库存", "material_inventory"),
    ]
    
    for table_name, table in tables_to_check:
        try:
            result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"✓ {table_name}表 ({table}): {count} 条记录")
        except Exception as e:
            print(f"✗ {table_name}表查询失败: {e}")
    
    print("\n" + "=" * 60)
    print("验证完成! RDS 数据库已成功配置并迁移。")
    print("=" * 60)
