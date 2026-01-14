#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
项目数据导入脚本
从旧数据库 sf_db_prod.sql 导入项目数据到 pear_admin.db 的 ums_project 表
"""

import re
import sqlite3
from datetime import datetime
from pathlib import Path
import sys

# 配置
SQL_FILE = r"旧数据库sf_db_prod.sql"
DB_FILE = r"instance\pear_admin.db"

# 字段映射关系
FIELD_MAPPING = {
    'xmid': 'id',  # 项目ID
    'xmmc': 'project_name',  # 项目名称（简称）
    'xmjc': 'project_full_name',  # 项目全称
    'xmgm': 'project_scale',  # 项目规模
    'ksrq': 'start_date',  # 开始日期
    'jsrq': 'end_date',  # 结束日期
    'xmzt': 'project_status',  # 项目状态
    'xmje': 'project_amount',  # 项目金额
    'fjid': 'attachments',  # 附件
}

# 项目规模映射
SCALE_MAPPING = {
    '1': '大型',
    '2': '中型',
    '3': '小型',
    '7': '特大型',
    '9': '其他',
}

# 项目状态映射
STATUS_MAPPING = {
    '01': '未开工',
    '02': '已开工',
    '03': '已开工未完成',
    '04': '已完成',
    '05': '验收中',
    '06': '已验收',
}


def parse_sql_insert(sql_line):
    """解析SQL INSERT语句"""
    # 匹配 INSERT INTO `base_project_info` VALUES ('6', '19泡泡公园', ...);
    pattern = r"INSERT INTO `base_project_info` VALUES \((.*?)\);"
    match = re.search(pattern, sql_line)
    
    if not match:
        return None
    
    values_str = match.group(1)
    
    # 简单的值分割（考虑引号内的逗号）
    values = []
    current = ''
    in_quote = False
    
    for char in values_str:
        if char == "'" and (not current or current[-1] != '\\'):
            in_quote = not in_quote
        elif char == ',' and not in_quote:
            values.append(current.strip().strip("'"))
            current = ''
            continue
        current += char
    
    # 添加最后一个值
    if current:
        values.append(current.strip().strip("'"))
    
    return values


def clean_value(value, field_type='text'):
    """清洗数据"""
    if not value or value == 'null' or value == 'NULL':
        return None
    
    value = value.strip()
    
    if field_type == 'date':
        # 日期格式：2018-10-31
        if value and value != '2000-01-01':  # 过滤无效日期
            try:
                return value  # SQLite可以直接存储字符串日期
            except:
                return None
        return None
    
    elif field_type == 'decimal':
        # 金额：96066813.00000 -> 96066813.00
        try:
            return float(value)
        except:
            return 0.0
    
    else:
        return value if value else None


def convert_to_project_data(values):
    """将SQL值转换为项目数据"""
    if len(values) < 15:
        return None
    
    # 旧数据库字段顺序
    # xmid, xmmc, xmjc, xmgm, ksrq, jsrq, xmzt, xmje, fjid, xh, lrrydm, lrsj, xgrydm, xgsj, yxbz
    
    # 过滤无效数据
    if values[14] == '0':  # yxbz = 0 表示无效
        return None
    
    project_scale = SCALE_MAPPING.get(values[3], values[3])
    project_status = STATUS_MAPPING.get(values[6], values[6])
    
    return {
        'id': int(values[0]) if values[0] else None,
        'project_name': clean_value(values[1]),  # 项目名称
        'project_full_name': clean_value(values[2]),  # 项目全称
        'project_scale': project_scale,
        'start_date': clean_value(values[4], 'date'),
        'end_date': clean_value(values[5], 'date'),
        'project_status': project_status,
        'project_amount': clean_value(values[7], 'decimal'),
        'attachments': clean_value(values[8]),
        'create_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def main():
    print("="*60)
    print("项目数据导入工具")
    print("="*60)
    print(f"源文件: {SQL_FILE}")
    print(f"目标数据库: {DB_FILE}")
    print("-" * 60)
    
    # 1. 读取SQL文件
    print("\n📖 读取SQL文件...")
    sql_file_path = Path(SQL_FILE)
    if not sql_file_path.exists():
        print(f"❌ 错误: 找不到文件 {SQL_FILE}")
        return
    
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 2. 提取INSERT语句
    print("🔍 提取项目数据...")
    insert_pattern = r"INSERT INTO `base_project_info` VALUES.*?;"
    inserts = re.findall(insert_pattern, content, re.DOTALL)
    
    print(f"   找到 {len(inserts)} 条INSERT语句")
    
    # 3. 解析数据
    print("\n🔄 解析数据...")
    projects = []
    
    for insert in inserts:
        values = parse_sql_insert(insert)
        if values:
            project_data = convert_to_project_data(values)
            if project_data:
                projects.append(project_data)
    
    print(f"   成功解析 {len(projects)} 条有效记录")
    
    if not projects:
        print("❌ 没有找到有效的项目数据")
        return
    
    # 显示前3条示例
    print("\n📋 数据示例（前3条）:")
    for i, project in enumerate(projects[:3], 1):
        print(f"\n  {i}. {project['project_name']}")
        print(f"     全称: {project['project_full_name']}")
        print(f"     规模: {project['project_scale']}")
        print(f"     状态: {project['project_status']}")
        print(f"     金额: {project['project_amount']}万元")
        print(f"     时间: {project['start_date']} ~ {project['end_date']}")
    
    # 4. 连接数据库
    print(f"\n📂 连接数据库 {DB_FILE}...")
    db_path = Path(DB_FILE)
    if not db_path.exists():
        print(f"❌ 错误: 找不到数据库文件 {DB_FILE}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 5. 清空现有数据（可选）
    confirm = input("\n⚠️  是否清空 ums_project 表现有数据? (y/n) [n]: ").strip().lower()
    if confirm == 'y':
        cursor.execute("DELETE FROM ums_project")
        print("✓ 已清空现有数据")
    
    # 6. 导入数据
    print("\n📥 开始导入...")
    success_count = 0
    error_count = 0
    
    for i, project in enumerate(projects, 1):
        try:
            cursor.execute("""
                INSERT INTO ums_project 
                (id, project_name, project_full_name, project_scale, 
                 start_date, end_date, project_status, project_amount, 
                 attachments, create_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project['id'],
                project['project_name'],
                project['project_full_name'],
                project['project_scale'],
                project['start_date'],
                project['end_date'],
                project['project_status'],
                project['project_amount'],
                project['attachments'],
                project['create_at'],
            ))
            success_count += 1
            
            if i % 10 == 0:
                print(f"   进度: {i}/{len(projects)}", end='\r')
                
        except Exception as e:
            error_count += 1
            print(f"\n   ❌ 导入失败 (ID: {project.get('id')}): {e}")
    
    conn.commit()
    conn.close()
    
    # 7. 汇总
    print(f"\n\n{'='*60}")
    print("导入完成!")
    print(f"{'='*60}")
    print(f"✅ 成功导入: {success_count} 条")
    if error_count > 0:
        print(f"❌ 导入失败: {error_count} 条")
    print(f"📊 总计: {len(projects)} 条")
    print(f"{'='*60}")
    
    # 8. 验证
    print("\n🔍 验证导入结果...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ums_project")
    count = cursor.fetchone()[0]
    print(f"   数据库中共有 {count} 条项目记录")
    
    cursor.execute("SELECT id, project_name, project_status FROM ums_project LIMIT 5")
    rows = cursor.fetchall()
    print("\n   前5条记录:")
    for row in rows:
        print(f"     ID {row[0]}: {row[1]} ({row[2]})")
    
    conn.close()
    
    print("\n✅ 全部完成!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
