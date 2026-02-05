"""
从SQLite数据库直接导入数据到RDS（跳过schema差异）
"""
import os
import sys
import sqlite3
from dotenv import load_dotenv
import pymysql
from decimal import Decimal

# 加载环境变量
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

# SQLite 数据库路径
SQLITE_DB = os.path.join(project_root, "instance", "pear_admin.db")

def get_mysql_connection():
    """获取MySQL连接"""
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def get_mysql_columns(cursor, table_name):
    """获取MySQL表的列名"""
    cursor.execute(f"SHOW COLUMNS FROM {table_name}")
    return {row['Field'] for row in cursor.fetchall()}

def migrate_table_data(sqlite_conn, mysql_conn, table_name):
    """迁移单个表的数据"""
    print(f"[MIGRATE] 正在迁移表: {table_name}")
    
    sqlite_cursor = sqlite_conn.cursor()
    mysql_cursor = mysql_conn.cursor()
    
    try:
        # 临时禁用外键检查
        mysql_cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # 获取MySQL表的列
        mysql_columns = get_mysql_columns(mysql_cursor, table_name)
        
        # 获取SQLite数据
        sqlite_cursor.execute(f"SELECT * FROM {table_name}")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            print(f"   [INFO] 表 {table_name} 为空")
            # 恢复外键检查
            mysql_cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            return
        
        # 获取SQLite列名
        sqlite_columns = [desc[0] for desc in sqlite_cursor.description]
        
        # 只保留在MySQL中存在的列
        valid_columns = [col for col in sqlite_columns if col in mysql_columns]
        
        if len(valid_columns) != len(sqlite_columns):
            skipped = set(sqlite_columns) - set(valid_columns)
            print(f"   [WARNING] 跳过不存在的列: {skipped}")
        
        # 清空目标表
        mysql_cursor.execute(f"DELETE FROM {table_name}")
        
        # 批量插入
        placeholders = ', '.join(['%s'] * len(valid_columns))
        columns_str = ', '.join([f'`{col}`' for col in valid_columns])
        insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
        
        count = 0
        batch_size = 100
        batch_data = []
        
        for row in rows:
            # 只取有效列的数据
            row_data = []
            for col in valid_columns:
                idx = sqlite_columns.index(col)
                value = row[idx]
                
                # 处理空字符串作为整数的情况
                if value == '' and col.endswith('_id'):
                    value = None
                
                row_data.append(value)
            
            batch_data.append(tuple(row_data))
            
            if len(batch_data) >= batch_size:
                mysql_cursor.executemany(insert_sql, batch_data)
                count += len(batch_data)
                batch_data = []
                print(f"   已导入 {count} 条记录...")
        
        # 插入剩余数据
        if batch_data:
            mysql_cursor.executemany(insert_sql, batch_data)
            count += len(batch_data)
        
        mysql_conn.commit()
        print(f"   [OK] 成功导入 {count} 条记录")
        
        # 恢复外键检查
        mysql_cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        
    except Exception as e:
        print(f"   [ERROR] 迁移失败: {e}")
        mysql_conn.rollback()
        # 确保恢复外键检查
        try:
            mysql_cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        except:
            pass
        import traceback
        traceback.print_exc()

def main():
    print("=" * 60)
    print("SQLite 到 RDS 数据迁移工具")
    print("=" * 60)
    
    if not os.path.exists(SQLITE_DB):
        print(f"[ERROR] SQLite数据库不存在: {SQLITE_DB}")
        return
    
    print(f"[INFO] 连接到 SQLite: {SQLITE_DB}")
    print(f"[INFO] 连接到 RDS: {os.getenv('MYSQL_HOST')}")
    
    try:
        # 连接数据库
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        mysql_conn = get_mysql_connection()
        
        # 获取所有表
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'alembic_%'")
        tables = [row[0] for row in sqlite_cursor.fetchall()]
        
        print(f"\n[INFO] 找到 {len(tables)} 个表需要迁移\n")
        
        # 迁移每个表
        for table in tables:
            migrate_table_data(sqlite_conn, mysql_conn, table)
        
        print("\n" + "=" * 60)
        print("[SUCCESS] 数据迁移完成!")
        print("=" * 60)
        
        # 关闭连接
        sqlite_conn.close()
        mysql_conn.close()
        
    except Exception as e:
        print(f"[ERROR] 迁移失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
