"""
清理重复的字典表
删除 ums_dictionary 和 ums_dictionary_detail 表
保留 base_dic 和 base_dic_detail 表（ORM 使用的表）
"""
import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from sqlalchemy import text, inspect

app = create_app()

def cleanup():
    with app.app_context():
        conn = db.engine.connect()
        inspector = inspect(conn)
        existing_tables = inspector.get_table_names()
        
        print("=" * 50)
        print("清理重复的字典表")
        print("=" * 50)
        print(f"当前数据库中的表: {len(existing_tables)} 个")
        
        # 要删除的表
        tables_to_drop = ['ums_dictionary_detail', 'ums_dictionary']
        
        try:
            # 禁用外键检查 (SQLite)
            try:
                conn.execute(text("PRAGMA foreign_keys = OFF"))
            except:
                pass
            
            # 禁用外键检查 (MySQL)
            try:
                conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            except:
                pass
            
            for table_name in tables_to_drop:
                if table_name in existing_tables:
                    print(f"删除表: {table_name}...")
                    try:
                        conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
                        conn.commit()
                        print(f"  ✅ 已删除 {table_name}")
                    except Exception as e:
                        print(f"  ❌ 删除失败: {e}")
                else:
                    print(f"表 {table_name} 不存在，跳过")
            
            # 重新启用外键检查
            try:
                conn.execute(text("PRAGMA foreign_keys = ON"))
            except:
                pass
            try:
                conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            except:
                pass
            
            print("\n" + "=" * 50)
            print("清理完成！")
            print("保留的字典表: base_dic, base_dic_detail")
            print("=" * 50)
            
        finally:
            conn.close()

if __name__ == "__main__":
    cleanup()
