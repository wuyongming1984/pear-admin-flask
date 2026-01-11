"""
SQLite 数据库导出为 MySQL 兼容的 SQL 文件

使用方法：
python export_sqlite_to_mysql.py

生成的 SQL 文件将保存为 mysql_export.sql
"""

import sqlite3
import os
import sys

# SQLite 数据库路径
SQLITE_DB_PATH = "instance/pear_admin.db"
# 输出的 MySQL SQL 文件
OUTPUT_SQL_FILE = "mysql_export.sql"

def sqlite_to_mysql_type(sqlite_type):
    """将 SQLite 数据类型转换为 MySQL 数据类型"""
    type_mapping = {
        'INTEGER': 'INT',
        'TEXT': 'TEXT',
        'REAL': 'DOUBLE',
        'BLOB': 'BLOB',
        'NUMERIC': 'DECIMAL',
    }
    sqlite_type_upper = sqlite_type.upper()
    for sqlite_t, mysql_t in type_mapping.items():
        if sqlite_t in sqlite_type_upper:
            return mysql_t
    return 'TEXT'  # 默认使用 TEXT

def export_sqlite_to_mysql_sql(sqlite_db_path, output_file):
    """导出 SQLite 数据库到 MySQL 兼容的 SQL 文件"""
    
    if not os.path.exists(sqlite_db_path):
        print(f"[ERROR] SQLite 数据库文件不存在: {sqlite_db_path}")
        print(f"\n请确认文件路径是否正确。")
        print(f"当前工作目录: {os.getcwd()}")
        return False
    
    print(f"[INFO] 正在读取 SQLite 数据库: {sqlite_db_path}")
    
    try:
        # 连接 SQLite 数据库
        conn = sqlite3.connect(sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            print("[ERROR] 数据库中没有找到任何表")
            return False
        
        print(f"[SUCCESS] 找到 {len(tables)} 个表: {', '.join(tables)}")
        
        # 打开输出文件
        with open(output_file, 'w', encoding='utf-8') as f:
            # 写入 MySQL 头部
            f.write("-- MySQL 数据导出文件\n")
            f.write("-- 从 SQLite 数据库导出\n")
            f.write(f"-- 源文件: {sqlite_db_path}\n\n")
            f.write("SET NAMES utf8mb4;\n")
            f.write("SET FOREIGN_KEY_CHECKS = 0;\n\n")
            
            # 遍历每个表
            for table in tables:
                print(f"[EXPORT] 正在导出表: {table}")
                
                # 获取表结构
                cursor.execute(f"PRAGMA table_info({table});")
                columns = cursor.fetchall()
                
                # 清空表（如果存在）
                f.write(f"-- 表: {table}\n")
                f.write(f"DELETE FROM `{table}`;\n\n")
                
                # 获取表数据
                cursor.execute(f"SELECT * FROM {table};")
                rows = cursor.fetchall()
                
                if rows:
                    # 获取列名
                    column_names = [col[1] for col in columns]
                    
                    # 分批插入数据（每 100 条一批）
                    batch_size = 100
                    for i in range(0, len(rows), batch_size):
                        batch = rows[i:i + batch_size]
                        
                        f.write(f"INSERT INTO `{table}` ({', '.join(['`' + col + '`' for col in column_names])}) VALUES\n")
                        
                        for idx, row in enumerate(batch):
                            values = []
                            for value in row:
                                if value is None:
                                    values.append("NULL")
                                elif isinstance(value, (int, float)):
                                    values.append(str(value))
                                elif isinstance(value, bytes):
                                    # 二进制数据转换为十六进制
                                    values.append(f"0x{value.hex()}")
                                else:
                                    # 字符串数据，转义特殊字符
                                    escaped = str(value).replace('\\', '\\\\').replace("'", "\\'")
                                    values.append(f"'{escaped}'")
                            
                            if idx == len(batch) - 1:
                                f.write(f"({', '.join(values)});\n")
                            else:
                                f.write(f"({', '.join(values)}),\n")
                        
                        f.write("\n")
                    
                    print(f"   [OK] 导出了 {len(rows)} 条记录")
                else:
                    print(f"   [INFO] 表为空")
                
                f.write("\n")
            
            f.write("SET FOREIGN_KEY_CHECKS = 1;\n")
        
        conn.close()
        
        print(f"\n[SUCCESS] 导出成功!")
        print(f"[INFO] MySQL SQL 文件已保存: {output_file}")
        print(f"[INFO] 文件大小: {os.path.getsize(output_file) / 1024:.2f} KB")
        return True
        
    except sqlite3.Error as e:
        print(f"[ERROR] SQLite 错误: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] 导出失败: {e}")
        return False

def main():
    print("=" * 60)
    print("SQLite 数据库导出工具")
    print("=" * 60)
    print()
    
    # 检查并导出数据库
    success = export_sqlite_to_mysql_sql(SQLITE_DB_PATH, OUTPUT_SQL_FILE)
    
    if success:
        print("\n" + "=" * 60)
        print("[NEXT] 下一步操作:")
        print("=" * 60)
        print()
        print("1. 上传 SQL 文件到服务器:")
        print(f"   scp {OUTPUT_SQL_FILE} root@8.159.138.234:/root/pear-admin-flask/")
        print()
        print("2. 在服务器上导入到 MySQL:")
        print(f"   cd /root/pear-admin-flask")
        print(f"   docker-compose exec -T mysql mysql -u root -pXfLA5Lz7OPhrVf4pdoSkqA== pear_admin < {OUTPUT_SQL_FILE}")
        print()
        print("3. 验证数据:")
        print(f"   docker-compose exec mysql mysql -u root -pXfLA5Lz7OPhrVf4pdoSkqA== pear_admin -e \"SHOW TABLES; SELECT COUNT(*) FROM ums_user;\"")
        print()
    else:
        print("\n[ERROR] 导出失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    main()
