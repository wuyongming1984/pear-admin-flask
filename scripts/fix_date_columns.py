"""
修复 base_dic 和 base_dic_detail 表的日期列类型
将 LONGBLOB 类型转换为 DATETIME 类型
"""
import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from sqlalchemy import text, inspect

app = create_app("prod")

def fix_date_columns():
    print("=" * 60)
    print("修复字典表日期列类型")
    print("=" * 60)
    
    with app.app_context():
        conn = db.engine.connect()
        
        try:
            # 要修复的表和列
            tables_to_fix = [
                ('base_dic', ['create_time', 'update_time']),
                ('base_dic_detail', ['create_time', 'update_time'])
            ]
            
            for table_name, columns in tables_to_fix:
                print(f"\n修复表: {table_name}")
                
                for col_name in columns:
                    print(f"  修复列: {col_name}")
                    try:
                        # 1. 先添加临时列
                        temp_col = f"{col_name}_temp"
                        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {temp_col} DATETIME NULL"))
                        conn.commit()
                        print(f"    ✅ 添加临时列 {temp_col}")
                        
                        # 2. 尝试转换数据（如果原列是BLOB，需要解析）
                        try:
                            # 尝试将 BLOB 数据转换为字符串再转为 DATETIME
                            conn.execute(text(f"""
                                UPDATE {table_name} 
                                SET {temp_col} = STR_TO_DATE(CONVERT({col_name} USING utf8mb4), '%Y-%m-%d %H:%i:%s')
                                WHERE {col_name} IS NOT NULL
                            """))
                            conn.commit()
                            print(f"    ✅ 转换数据成功")
                        except Exception as e:
                            print(f"    ⚠️ 数据转换警告: {e}")
                            # 如果转换失败，设置为当前时间
                            conn.execute(text(f"UPDATE {table_name} SET {temp_col} = NOW() WHERE {temp_col} IS NULL"))
                            conn.commit()
                        
                        # 3. 删除原列
                        conn.execute(text(f"ALTER TABLE {table_name} DROP COLUMN {col_name}"))
                        conn.commit()
                        print(f"    ✅ 删除原列 {col_name}")
                        
                        # 4. 重命名临时列
                        conn.execute(text(f"ALTER TABLE {table_name} CHANGE {temp_col} {col_name} DATETIME NULL"))
                        conn.commit()
                        print(f"    ✅ 重命名为 {col_name}")
                        
                    except Exception as e:
                        print(f"    ❌ 修复失败: {e}")
                        # 尝试清理临时列
                        try:
                            conn.execute(text(f"ALTER TABLE {table_name} DROP COLUMN {temp_col}"))
                            conn.commit()
                        except:
                            pass
            
            print("\n" + "=" * 60)
            print("修复完成！")
            print("=" * 60)
            
        except Exception as e:
            print(f"执行失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()

if __name__ == "__main__":
    fix_date_columns()
