#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
本地到远程数据库同步脚本
将本地 SQLite 数据同步到远程 MySQL
"""

import sqlite3
import pymysql
import sys
from datetime import datetime
from pathlib import Path

# 配置
LOCAL_DB = r"d:\pear_admin\pear-admin-flask\instance\pear_admin.db"
REMOTE_HOST = "8.159.138.234"
REMOTE_PORT = 3306
REMOTE_USER = "root"
REMOTE_DB = "pear_admin"

def sync_table(table_name, sqlite_conn, mysql_conn):
    """同步单张表"""
    print(f"\n🔄 正在同步表: {table_name}...")
    
    # 1. 读取 SQLite 数据
    s_cursor = sqlite_conn.cursor()
    try:
        s_cursor.execute(f"SELECT * FROM {table_name}")
        rows = s_cursor.fetchall()
        columns = [description[0] for description in s_cursor.description]
        print(f"   本地读取到 {len(rows)} 条记录")
    except Exception as e:
        print(f"   ⚠️ 跳过: 本地表不存在或读取失败 ({e})")
        return

    if not rows:
        print("   本地表为空，跳过")
        return

    # 2. 写入 MySQL
    m_cursor = mysql_conn.cursor()
    try:
        # 清空目标表
        m_cursor.execute(f"TRUNCATE TABLE {table_name}")
        
        # 构建 INSERT 语句
        placeholders = ', '.join(['%s'] * len(columns))
        col_names = ', '.join([f"`{c}`" for c in columns])
        sql = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"
        
        # 批量执行
        success_count = 0
        batch_size = 100
        
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            try:
                m_cursor.executemany(sql, batch)
                mysql_conn.commit()
                success_count += len(batch)
                print(f"   已导入 {success_count}/{len(rows)}...", end='\r')
            except Exception as e:
                print(f"\n   ❌ 批次导入失败: {e}")
                # 尝试逐条导入以定位问题
                for row in batch:
                    try:
                        m_cursor.execute(sql, row)
                    except:
                        pass
        
        print(f"\n   ✅ 同步完成")
        
    except Exception as e:
        print(f"   ❌ MySQL 操作失败: {e}")
        mysql_conn.rollback()

def main():
    print("="*60)
    print("数据库同步工具: 本地 SQLite -> 远程 MySQL")
    print("="*60)
    print(f"本地库: {LOCAL_DB}")
    print(f"远程库: {REMOTE_HOST} ({REMOTE_DB})")
    print("-" * 60)

    # 获取密码
    if len(sys.argv) > 1:
        pwd = sys.argv[1]
    else:
        pwd = input("请输入远程 MySQL root 密码: ").strip()

    # 连接 SQLite
    try:
        sqlite_conn = sqlite3.connect(LOCAL_DB)
    except Exception as e:
        print(f"❌ 无法连接本地 SQLite: {e}")
        return

    # 连接 MySQL
    try:
        mysql_conn = pymysql.connect(
            host=REMOTE_HOST,
            port=REMOTE_PORT,
            user=REMOTE_USER,
            password=pwd,
            database=REMOTE_DB
        )
        print("✓ 远程 MySQL 连接成功")
    except Exception as e:
        print(f"❌ 无法连接远程 MySQL: {e}")
        print("提示: 请检查防火墙设置或确认 Navicat 是否使用了 SSH 隧道。")
        print("如果是通过 SSH 隧道连接，请优先使用 Navicat 的【数据传输】功能。")
        return

    # 要同步的表列表
    # 核心权限和字典表
    tables = [
        'ums_rights',       # 菜单和权限定义 (关键：决定首页显示什么)
        'ums_role',         # 角色
        'ums_role_rights',  # 角色-权限关联
        'ums_dictionary',   # 数据字典 (下拉框选项等)
        'ums_supplier'      # 之前已有的
    ]
    
    # 询问是否同步所有表
    print(f"\n默认同步表: {', '.join(tables)}")
    choice = input("是否继续? (y/n) [y]: ")
    if choice.lower() == 'n':
        return

    for table in tables:
        sync_table(table, sqlite_conn, mysql_conn)

    print("\n" + "="*60)
    print("所有同步任务完成！")

    sqlite_conn.close()
    mysql_conn.close()

if __name__ == "__main__":
    main()
