"""
重建 nursery_transaction 表，修复SQLite到MySQL的类型映射问题
运行方式：python scripts/fix_nursery_table.py
"""
import sqlite3
import os

# 数据库路径
db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'pear_admin.db')

def fix_nursery_transaction():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nursery_transaction'")
        if not cursor.fetchone():
            print("表 nursery_transaction 不存在，无需修复")
            return
        
        # 2. 备份现有数据
        print("备份现有数据...")
        cursor.execute("SELECT * FROM nursery_transaction")
        data = cursor.fetchall()
        cursor.execute("PRAGMA table_info(nursery_transaction)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"找到 {len(data)} 条记录")
        
        # 3. 删除旧表
        print("删除旧表...")
        cursor.execute("DROP TABLE nursery_transaction")
        
        # 4. 创建新表，使用明确的类型定义
        # SQLite会存储这些类型信息，Navicat可以据此做更好的映射
        print("创建新表...")
        cursor.execute("""
            CREATE TABLE nursery_transaction (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_no VARCHAR(50) NOT NULL,
                type VARCHAR(10) NOT NULL,
                plant_id INTEGER,
                plant_name VARCHAR(100),
                spec VARCHAR(100),
                unit VARCHAR(20),
                quantity DECIMAL(10,2) NOT NULL,
                price DECIMAL(10,2),
                total_price DECIMAL(12,2),
                operator VARCHAR(50),
                destination VARCHAR(100),
                location VARCHAR(100),
                remark VARCHAR(255),
                create_at DATETIME
            )
        """)
        
        # 5. 创建索引
        print("创建索引...")
        cursor.execute("CREATE INDEX ix_nursery_transaction_order_no ON nursery_transaction(order_no)")
        
        # 6. 恢复数据
        if data:
            print("恢复数据...")
            placeholders = ','.join(['?' for _ in columns])
            cursor.executemany(f"INSERT INTO nursery_transaction ({','.join(columns)}) VALUES ({placeholders})", data)
        
        conn.commit()
        print(f"修复完成！共恢复 {len(data)} 条记录")
        
    except Exception as e:
        conn.rollback()
        print(f"修复失败: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    fix_nursery_transaction()
