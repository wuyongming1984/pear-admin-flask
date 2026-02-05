import os
import sys
import pymysql
from dotenv import load_dotenv

# 加载 .env
# 假设脚本在 scripts/ 目录下，.env 在上一级目录
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
env_path = os.path.join(project_root, '.env')

if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"[INFO] 已加载环境变量: {env_path}")
else:
    print(f"[WARNING] 未找到 .env 文件: {env_path}")

def import_sql_to_rds(sql_file):
    # 获取数据库配置
    host = os.getenv("MYSQL_HOST")
    port = int(os.getenv("MYSQL_PORT", 3306))
    user = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")
    database = os.getenv("MYSQL_DATABASE")

    if not all([host, user, password, database]):
        print("[ERROR] 缺失数据库连接配置 (MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE)")
        return False

    print(f"[INFO] 连接 RDS: {host}:{port} (User: {user}, DB: {database})")
    
    try:
        # 连接数据库
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            port=port,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        # 创建数据库（如果不存在）
        # 注意：通常 RDS 账号可能没有创建数据库的权限，但我们尝试一下，或者假设库已存在
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            conn.select_db(database)
        except Exception as e:
            print(f"[WARNING] 创建/选择数据库失败，尝试直接连接指定库: {e}")
            conn.select_db(database)

        print("[INFO] 连接成功，准备导入 SQL...")

        # 读取 SQL 文件
        if not os.path.exists(sql_file):
            print(f"[ERROR] SQL 文件不存在: {sql_file}")
            return False

        with conn.cursor() as cursor:
            # 临时关闭外键检查
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            
            with open(sql_file, 'r', encoding='utf-8') as f:
                # 简单解析 SQL：按分号分割语句
                # 注意：这种方式不支持存储过程或包含分号的字符串，但对于 export_sqlite_to_mysql.py 生成的标准 INSERT 语句是足够的
                content = f.read()
                statements = content.split(';\n')
                
                total = len(statements)
                count = 0
                
                for stmt in statements:
                    stmt = stmt.strip()
                    if not stmt or stmt.startswith('--') or stmt.startswith('/*'):
                        continue
                    
                    try:
                        cursor.execute(stmt)
                        count += 1
                        if count % 50 == 0:
                            print(f"   已执行 {count} 条语句...")
                    except Exception as e:
                        print(f"[ERROR] 执行语句失败:\n{stmt[:100]}...\n错误: {e}")
            
            # 恢复外键检查
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            conn.commit()

        print(f"\n[SUCCESS] 导入完成! 共执行 {count} 条语句。")
        conn.close()
        return True

    except pymysql.MySQLError as e:
        print(f"[ERROR] 数据库连接或执行错误: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] 未知错误: {e}")
        return False

if __name__ == "__main__":
    sql_file_path = os.path.join(project_root, "mysql_export.sql")
    print("=" * 60)
    print("MySQL/RDS 数据导入工具")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        sql_file_path = sys.argv[1]
    
    import_sql_to_rds(sql_file_path)
