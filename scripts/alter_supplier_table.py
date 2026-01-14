#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修改ums_supplier表的account_number字段类型
从INTEGER改为VARCHAR
"""

import sqlite3
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "instance" / "pear_admin.db"


def alter_table():
    """修改表结构"""
    print(f"开始修改数据库表结构...")
    print(f"数据库路径: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # SQLite不支持直接ALTER COLUMN，需要重建表
        print("\n1. 创建新表...")
        cursor.execute("""
            CREATE TABLE ums_supplier_new (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                type_id INTEGER NOT NULL,
                name VARCHAR(128) NOT NULL,
                contact_person VARCHAR(128) NOT NULL,
                phone VARCHAR(32) NOT NULL,
                email VARCHAR(64),
                bank_name VARCHAR(128) NOT NULL,
                account_number VARCHAR(128) NOT NULL,
                address TEXT,
                remark TEXT,
                create_at DATETIME NOT NULL
            )
        """)
        
        # 复制数据（将INTEGER转为VARCHAR）
        print("2. 复制现有数据...")
        cursor.execute("""
            INSERT INTO ums_supplier_new 
            (id, type_id, name, contact_person, phone, email, bank_name, 
             account_number, address, remark, create_at)
            SELECT 
                id, type_id, name, contact_person, phone, email, bank_name,
                CAST(account_number AS VARCHAR), address, remark, create_at
            FROM ums_supplier
        """)
        
        # 删除旧表
        print("3. 删除旧表...")
        cursor.execute("DROP TABLE ums_supplier")
        
        # 重命名新表
        print("4. 重命名新表...")
        cursor.execute("ALTER TABLE ums_supplier_new RENAME TO ums_supplier")
        
        conn.commit()
        
        # 验证
        cursor.execute("SELECT COUNT(*) FROM ums_supplier")
        count = cursor.fetchone()[0]
        
        print(f"\n✅ 表结构修改完成！")
        print(f"   当前记录数: {count}")
        
    except Exception as e:
        print(f"\n❌ 修改失败: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == '__main__':
    alter_table()
