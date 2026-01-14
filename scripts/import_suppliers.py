#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
供应商数据导入脚本
从旧数据库 sf_db_prod.sql 导入供应商数据到 ums_supplier 表
"""

import re
import sqlite3
from datetime import datetime
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "instance" / "pear_admin.db"
SQL_FILE = Path(__file__).parent.parent / "旧数据库sf_db_prod.sql"


def parse_insert_values(insert_line):
    """
    解析INSERT语句中的VALUES部分
    INSERT INTO `base_supplier_info` VALUES ('8', '1', '安吉国海园林绿化工程有限公司', ...);
    """
    # 提取VALUES后面的内容
    match = re.search(r"VALUES\s*\((.*?)\);", insert_line, re.DOTALL)
    if not match:
        return None
    
    values_str = match.group(1)
    
    # 分割字段值（处理引号内的逗号）
    values = []
    in_quote = False
    current = []
    i = 0
    
    while i < len(values_str):
        char = values_str[i]
        
        if char == "'" and (i == 0 or values_str[i-1] != '\\'):
            in_quote = not in_quote
            current.append(char)
        elif char == ',' and not in_quote:
            # 字段分隔符
            field = ''.join(current).strip()
            values.append(field)
            current = []
        else:
            current.append(char)
        
        i += 1
    
    # 添加最后一个字段
    if current:
        field = ''.join(current).strip()
        values.append(field)
    
    return values


def clean_value(value):
    """清理字段值"""
    if value in ['null', 'NULL', '']:
        return None
    
    # 去除引号
    if value.startswith("'") and value.endswith("'"):
        value = value[1:-1]
    
    # 处理转义字符
    value = value.replace("\\'", "'")
    value = value.replace("\\r\\n", "\n")
    value = value.replace("\\n", "\n")
    
    return value.strip() if value else None


def convert_to_supplier_data(values):
    """
    将旧数据库的字段转换为新系统的字段
    
    旧字段顺序：
    gysid, gyslx, gysmc, lxr, lxdh, khyh, yhzh, ksrq, jsrq, bz, 
    lrrydm, lrsj, xgrydm, xgsj, yxbz
    """
    if len(values) < 15:
        return None
    
    # 清理所有值
    cleaned = [clean_value(v) for v in values]
    
    gysid, gyslx, gysmc, lxr, lxdh, khyh, yhzh = cleaned[0:7]
    ksrq, jsrq, bz, lrrydm, lrsj, xgrydm, xgsj, yxbz = cleaned[7:15]
    
    # 跳过无效记录
    if yxbz == '0':
        return None
    
    # 转换 type_id
    try:
        type_id = int(gyslx) if gyslx and gyslx in ['1', '2'] else 1
    except:
        type_id = 1
    
    # 转换 name（最多128字符）
    name = gysmc[:128] if gysmc else '未命名供应商'
    
    # 转换 contact_person
    contact_person = lxr if lxr else '未知'
    
    # 转换 phone
    phone = lxdh.replace(' ', '') if lxdh and lxdh != '0' else '0'
    phone = phone[:32]  # 最多32字符
    
    # 转换 bank_name
    bank_name = khyh if khyh and khyh != '0' else '-'
    bank_name = bank_name[:128]  # 最多128字符
    
    # 转换 account_number（保存为字符串）
    if yhzh and yhzh != '0':
        account_number = yhzh.strip()  # 保留原始格式，只去除首尾空格
    else:
        account_number = '0'
    
    # 转换 create_at
    if lrsj:
        try:
            create_at = datetime.strptime(lrsj, '%Y-%m-%d %H:%M:%S')
        except:
            create_at = datetime.now()
    else:
        create_at = datetime.now()
    
    return {
        'old_id': int(gysid) if gysid else None,
        'type_id': type_id,
        'name': name,
        'contact_person': contact_person,
        'phone': phone,
        'email': None,
        'bank_name': bank_name,
        'account_number': account_number,
        'address': None,
        'remark': bz,
        'create_at': create_at.strftime('%Y-%m-%d %H:%M:%S')
    }


def import_suppliers():
    """执行导入"""
    print(f"开始导入供应商数据...")
    print(f"SQL文件路径: {SQL_FILE}")
    print(f"数据库路径: {DB_PATH}")
    print()
    
    if not SQL_FILE.exists():
        print(f"❌ SQL文件不存在: {SQL_FILE}")
        return
    
    if not DB_PATH.exists():
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        return
    
    # 读取SQL文件
    print("📖 读取SQL文件...")
    with open(SQL_FILE, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 提取所有INSERT语句
    insert_pattern = r"INSERT INTO `base_supplier_info` VALUES.*?;"
    insert_statements = re.findall(insert_pattern, sql_content, re.DOTALL)
    
    print(f"✓ 找到 {len(insert_statements)} 条INSERT语句")
    
    # 解析数据
    print("\n🔄 解析和清洗数据...")
    suppliers = []
    skipped = 0
    
    for insert_line in insert_statements:
        values = parse_insert_values(insert_line)
        if not values:
            skipped += 1
            continue
        
        supplier_data = convert_to_supplier_data(values)
        if supplier_data:
            suppliers.append(supplier_data)
        else:
            skipped += 1
    
    print(f"✓ 解析成功: {len(suppliers)} 条")
    print(f"✓ 跳过无效: {skipped} 条")
    
    # 连接数据库
    print("\n💾 写入数据库...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查表是否存在
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='ums_supplier'
    """)
    if not cursor.fetchone():
        print("❌ ums_supplier表不存在")
        conn.close()
        return
    
    # 清空现有数据（可选）
    print("⚠️  清空现有供应商数据...")
    cursor.execute("DELETE FROM ums_supplier")
    
    # 插入数据
    success_count = 0
    error_count = 0
    
    for supplier in suppliers:
        try:
            cursor.execute("""
                INSERT INTO ums_supplier 
                (type_id, name, contact_person, phone, email, bank_name, 
                 account_number, address, remark, create_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                supplier['type_id'],
                supplier['name'],
                supplier['contact_person'],
                supplier['phone'],
                supplier['email'],
                supplier['bank_name'],
                supplier['account_number'],
                supplier['address'],
                supplier['remark'],
                supplier['create_at']
            ))
            success_count += 1
        except Exception as e:
            error_count += 1
            print(f"  ❌ 导入失败: {supplier['name']} - {e}")
    
    # 提交事务
    conn.commit()
    
    # 验证
    cursor.execute("SELECT COUNT(*) FROM ums_supplier")
    final_count = cursor.fetchone()[0]
    
    conn.close()
    
    # 输出结果
    print(f"\n{'='*60}")
    print(f"✅ 导入完成！")
    print(f"{'='*60}")
    print(f"📊 统计信息：")
    print(f"  - SQL文件记录数: {len(insert_statements)}")
    print(f"  - 有效记录数: {len(suppliers)}")
    print(f"  - 成功导入: {success_count}")
    print(f"  - 导入失败: {error_count}")
    print(f"  - 数据库最终记录数: {final_count}")
    print(f"{'='*60}")
    
    # 显示示例数据
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, contact_person, phone FROM ums_supplier LIMIT 5")
    rows = cursor.fetchall()
    
    if rows:
        print(f"\n📋 示例数据（前5条）：")
        print(f"{'ID':<5} {'供应商名称':<30} {'联系人':<15} {'电话':<20}")
        print(f"{'-'*75}")
        for row in rows:
            print(f"{row[0]:<5} {row[1]:<30} {row[2]:<15} {row[3]:<20}")
    
    conn.close()


if __name__ == '__main__':
    import_suppliers()
