#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
旧数据库一键导入工具
从 旧数据库sf_db_prod.sql 导入所有数据到 pear_admin.db

支持的表：
- ums_supplier（供应商）
- ums_project（项目）
- ums_order（订单）
- ums_pay（付款单）

使用方法：
1. 全量导入：python scripts/sync_from_old_db.py --all
2. 只导入订单：python scripts/sync_from_old_db.py --orders
3. 只导入付款单：python scripts/sync_from_old_db.py --pays
4. 增量更新：python scripts/sync_from_old_db.py --incremental
"""

import re
import sqlite3
from datetime import datetime
from pathlib import Path
import sys
import argparse

# 配置
SQL_FILE = r"旧数据库sf_db_prod.sql"
DB_FILE = r"instance\pear_admin.db"

# 状态映射
PAYMENT_STATUS_MAPPING = {
    '1': '未付款',
    '2': '已付款',
    '3': '部分付款',
    '4': '已作废',
}

PROJECT_SCALE_MAPPING = {
    '1': '大型', '2': '中型', '3': '小型', '7': '特大型', '9': '其他',
}

PROJECT_STATUS_MAPPING = {
    '01': '未开工', '02': '已开工', '03': '已开工未完成', 
    '04': '已完成', '05': '验收中', '06': '已验收',
}


def parse_values(sql_line):
    """解析INSERT语句中的VALUES"""
    pattern = r"VALUES \((.*?)\);"
    match = re.search(pattern, sql_line)
    if not match:
        return None
    
    values_str = match.group(1)
    values = []
    current = ''
    in_quote = False
    
    for char in values_str:
        if char == "'" and (not current or current[-1] != '\\'):
            in_quote = not in_quote
        elif char == ',' and not in_quote:
            val = current.strip().strip("'")
            values.append(None if val in ('null', 'NULL', '') else val)
            current = ''
            continue
        current += char
    
    if current:
        val = current.strip().strip("'")
        values.append(None if val in ('null', 'NULL', '') else val)
    
    return values


def read_sql_file():
    """读取SQL文件"""
    print("📖 读取SQL文件...")
    sql_path = Path(SQL_FILE)
    if not sql_path.exists():
        print(f"❌ 错误: 找不到 {SQL_FILE}")
        sys.exit(1)
    
    with open(sql_path, 'r', encoding='utf-8') as f:
        return f.read()


def extract_inserts(content, table_name):
    """提取指定表的INSERT语句"""
    pattern = rf"INSERT INTO `{table_name}` VALUES.*?;"
    return re.findall(pattern, content, re.DOTALL)


def import_suppliers(conn, content, mode='full'):
    """导入供应商数据"""
    print("\n" + "="*60)
    print("📦 导入供应商数据 (base_supplier_info → ums_supplier)")
    print("="*60)
    
    inserts = extract_inserts(content, 'base_supplier_info')
    print(f"  📊 SQL记录数: {len(inserts)}")
    
    cursor = conn.cursor()
    
    if mode == 'full':
        cursor.execute("DELETE FROM ums_supplier")
        print("  ✓ 已清空现有数据")
    
    success, errors = 0, 0
    existing = set()
    if mode == 'incremental':
        cursor.execute("SELECT id FROM ums_supplier")
        existing = {row[0] for row in cursor.fetchall()}
    
    for insert in inserts:
        values = parse_values(insert)
        if not values or len(values) < 15:
            errors += 1
            continue
        
        # base_supplier_info 字段顺序:
        # 0:gysid, 1:gyslx, 2:gysmc, 3:lxr, 4:lxdh, 5:khyh,
        # 6:yhzh, 7:dz, 8:bz, 9-12:null, 13:lrsj, 14:yxbz
        
        # 过滤无效记录
        if values[14] == '0':  # yxbz
            continue
        
        supplier_id = int(values[0]) if values[0] else None
        if mode == 'incremental' and supplier_id in existing:
            continue
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO ums_supplier 
                (id, type_id, name, contact_person, phone, 
                 bank_name, account_number, address, remark, create_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                supplier_id,
                values[1],  # type_id (gyslx)
                values[2],  # name (gysmc)
                values[3],  # contact_person (lxr)
                values[4],  # phone (lxdh)
                values[5],  # bank_name (khyh)
                values[6],  # account_number (yhzh)
                values[7],  # address (dz)
                values[8],  # remark (bz)
                values[13] or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))
            success += 1
        except Exception as e:
            errors += 1
    
    conn.commit()
    print(f"  ✅ 成功: {success} 条, ❌ 失败: {errors} 条")
    return success


def import_projects(conn, content, mode='full'):
    """导入项目数据"""
    print("\n" + "="*60)
    print("📦 导入项目数据 (base_project_info → ums_project)")
    print("="*60)
    
    inserts = extract_inserts(content, 'base_project_info')
    print(f"  📊 SQL记录数: {len(inserts)}")
    
    cursor = conn.cursor()
    
    if mode == 'full':
        cursor.execute("DELETE FROM ums_project")
        print("  ✓ 已清空现有数据")
    
    success, errors = 0, 0
    
    for insert in inserts:
        values = parse_values(insert)
        if not values or len(values) < 15:
            continue
        
        # 过滤无效记录
        if values[14] == '0':  # yxbz
            continue
        
        # base_project_info: 0:xmid, 1:xmmc, 2:xmjc, 3:xmgm, 4:ksrq, 5:jsrq,
        #                    6:xmzt, 7:xmje, 8:fjid, ...
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO ums_project 
                (id, project_name, project_full_name, project_scale,
                 start_date, end_date, project_status, project_amount,
                 attachments, create_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(values[0]) if values[0] else None,
                values[1],  # project_name
                values[2],  # project_full_name
                PROJECT_SCALE_MAPPING.get(values[3], values[3]),
                values[4] if values[4] and values[4] != '2000-01-01' else None,
                values[5] if values[5] and values[5] != '2000-01-01' else None,
                PROJECT_STATUS_MAPPING.get(values[6], values[6]),
                values[7],  # project_amount
                values[8],  # attachments
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))
            success += 1
        except Exception as e:
            errors += 1
    
    conn.commit()
    print(f"  ✅ 成功: {success} 条, ❌ 失败: {errors} 条")
    return success


def import_orders(conn, content, mode='full'):
    """导入订单数据"""
    print("\n" + "="*60)
    print("📦 导入订单数据 (core_order_info → ums_order)")
    print("="*60)
    
    inserts = extract_inserts(content, 'core_order_info')
    print(f"  📊 SQL记录数: {len(inserts)}")
    
    cursor = conn.cursor()
    
    if mode == 'full':
        cursor.execute("DELETE FROM ums_order")
        print("  ✓ 已清空现有数据")
    
    # 获取项目映射
    cursor.execute("SELECT id, project_name FROM ums_project")
    project_names = {row[0]: row[1] for row in cursor.fetchall()}
    
    success, errors, skipped = 0, 0, 0
    existing_numbers = set()
    
    for insert in inserts:
        values = parse_values(insert)
        if not values or len(values) < 22:
            continue
        
        # 过滤无效记录
        if values[21] == '0':  # yxbz
            skipped += 1
            continue
        
        # core_order_info: 0:ddid, 1:ddbh, 2:xmid, 3:ddlx, 4:clmc, 5:clfxmc,
        #                  6:xdrq, 7:ddje, 8:jsje, 9:gyslxr, 10:gyslxdh, ...
        
        order_number = values[1]
        if not order_number or order_number in existing_numbers:
            skipped += 1
            continue
        
        existing_numbers.add(order_number)
        
        project_id = int(values[2]) if values[2] and values[2].isdigit() else None
        project_name = project_names.get(project_id, f"项目{project_id}" if project_id else None)
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO ums_order 
                (order_number, material_name, project_name, supplier_id,
                 supplier_contact_person, contact_phone, cutting_time, estimated_arrival_time,
                 material_details, order_amount, material_manager,
                 sub_project_manager, attachments, create_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_number,
                values[4] or '未命名材料',  # material_name
                project_name,
                None,  # supplier_id (暂时为空)
                values[9], # supplier_contact_person (gyslxr)
                values[10],  # contact_phone
                values[6],  # cutting_time (下单日期)
                None,  # estimated_arrival_time
                values[5],  # material_details
                values[7],  # order_amount
                None,  # material_manager
                None,  # sub_project_manager
                None,  # attachments
                values[17] or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))
            success += 1
        except Exception as e:
            errors += 1
    
    conn.commit()
    print(f"  ✅ 成功: {success} 条, ❌ 失败: {errors} 条, ⊘ 跳过: {skipped} 条")
    return success


def import_payers(conn, content, mode='full'):
    print("\n📦 开始导入付款单位数据...")
    cursor = conn.cursor()
    
    # 查找 base_payer_info 的 INSERT 语句
    payer_inserts = []
    lines = content.split('\n')
    for line in lines:
        if line.startswith("INSERT INTO `base_payer_info`"):
            payer_inserts.append(line)
            
    if not payer_inserts:
        print("⚠️ 未找到付款单位数据")
        return

    print(f"找到 {len(payer_inserts)} 条付款单位记录")
    
    # 获取现有付款单位ID
    existing = set()
    if mode == 'incremental':
        cursor.execute("SELECT id FROM ums_payer")
        existing = {row[0] for row in cursor.fetchall()}
        
    success = 0
    errors = 0
    skipped = 0
    
    for insert in payer_inserts:
        values = parse_values(insert)
        if not values or len(values) < 11:
            errors += 1
            continue
            
        # base_payer_info 字段顺序:
        # 0:fkdwid, 1:fkdwlx, 2:fkdwmc, 3:fkdwyh, 4:fkdwyhzh, 
        # 5:bz, 6:lrrydm, 7:lrsj, 8:xgrydm, 9:xgsj, 10:yxbz
        
        # 过滤无效记录
        if values[10] == '0':
             continue
             
        payer_id = int(values[0]) if values[0] else None
        
        if mode == 'incremental' and payer_id in existing:
            skipped += 1
            continue
            
        try:
             cursor.execute("""
                INSERT OR REPLACE INTO ums_payer
                (id, type_id, name, bank_name, account_number, remark, create_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                payer_id,
                int(values[1]) if values[1] and values[1].isdigit() else 1, # fkdwlx
                values[2], # fkdwmc
                values[3], # fkdwyh
                values[4], # fkdwyhzh
                values[5], # bz
                values[7] or datetime.now().strftime("%Y-%m-%d %H:%M:%S") # lrsj
            ))
             success += 1
        except Exception as e:
            print(f"导入出错 ID {values[0]}: {e}")
            errors += 1
            
    conn.commit()
    print(f"✅ 付款单位导入完成: 成功 {success}, 跳过 {skipped}, 错误 {errors}")


def import_pays(conn, content, mode='full'):
    """导入付款单数据"""
    print("\n" + "="*60)
    print("📦 导入付款单数据 (core_payment_request_detail_info → ums_pay)")
    print("="*60)
    
    # 获取付款申请和订单映射
    request_inserts = extract_inserts(content, 'core_payment_request_info')
    detail_inserts = extract_inserts(content, 'core_payment_request_detail_info')
    order_inserts = extract_inserts(content, 'core_order_info')
    
    print(f"  📊 付款申请: {len(request_inserts)}, 付款单: {len(detail_inserts)}, 订单: {len(order_inserts)}")
    
    # 构建映射
    request_mapping = {}  # fksqid → {ddid, fkyt}
    for insert in request_inserts:
        values = parse_values(insert)
        if values and len(values) >= 7:
            request_mapping[values[0]] = {'ddid': values[3], 'fkyt': values[5]}
    
    order_id_to_number = {}  # ddid → ddbh
    for insert in order_inserts:
        values = parse_values(insert)
        if values and len(values) >= 2 and values[0] and values[1]:
            order_id_to_number[values[0]] = values[1]
    
    cursor = conn.cursor()
    
    if mode == 'full':
        cursor.execute("DELETE FROM ums_pay")
        print("  ✓ 已清空现有数据")
    
    # 获取本地订单映射
    cursor.execute("SELECT id, order_number FROM ums_order")
    order_mapping = {row[1]: row[0] for row in cursor.fetchall() if row[1]}
    
    # 获取有效供应商
    cursor.execute("SELECT id FROM ums_supplier")
    supplier_ids = {row[0] for row in cursor.fetchall()}
    
    # 获取有效付款单位
    cursor.execute("SELECT id FROM ums_payer")
    payer_ids = {row[0] for row in cursor.fetchall()}
    
    success, errors, skipped = 0, 0, 0
    existing_numbers = set()
    
    for insert in detail_inserts:
        values = parse_values(insert)
        if not values or len(values) < 18:
            continue
        
        # 过滤无效记录
        if values[17] == '0':  # yxbz
            skipped += 1
            continue
        
        pay_number = values[1]
        if not pay_number or pay_number in existing_numbers:
            skipped += 1
            continue
        
        existing_numbers.add(pay_number)
        
        # 获取关联订单
        fksqid = values[2]
        if not fksqid or fksqid not in request_mapping:
            skipped += 1
            continue
        
        req_info = request_mapping[fksqid]
        old_ddid = req_info['ddid']
        
        if not old_ddid or old_ddid not in order_id_to_number:
            skipped += 1
            continue
        
        order_number = order_id_to_number[old_ddid]
        if order_number not in order_mapping:
            skipped += 1
            continue
        
        new_order_id = order_mapping[order_number]
        
        # 付款单位ID (values[7]) -> 对应 ums_payer
        payer_id = int(values[7]) if values[7] and values[7].isdigit() and int(values[7]) in payer_ids else None
        
        # 收款单位ID (values[8]) -> 对应 ums_supplier
        payee_id = int(values[8]) if values[8] and values[8].isdigit() and int(values[8]) in supplier_ids else None
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO ums_pay 
                (pay_number, order_id, payer_supplier_id, payee_supplier_id,
                 payment_purpose, current_payment_amount, invoice_amount,
                 payment_status, handler, create_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pay_number,
                new_order_id,
                payer_id,
                payee_id,
                req_info['fkyt'],
                values[3],  # sfje
                values[4],  # kpje
                PAYMENT_STATUS_MAPPING.get(values[12], values[12]),
                None,  # handler
                values[14] or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))
            success += 1
        except Exception as e:
            errors += 1
    
    conn.commit()
    print(f"  ✅ 成功: {success} 条, ❌ 失败: {errors} 条, ⊘ 跳过: {skipped} 条")
    return success


def print_summary(conn):
    """打印汇总信息"""
    print("\n" + "="*60)
    print("📊 数据库汇总")
    print("="*60)
    
    cursor = conn.cursor()
    tables = [
        ('ums_supplier', '供应商'),
        ('ums_project', '项目'),
        ('ums_order', '订单'),
        ('ums_pay', '付款单'),
    ]
    
    for table, name in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {name}: {count} 条")


def main():
    parser = argparse.ArgumentParser(description='旧数据库一键导入工具')
    parser.add_argument('--all', action='store_true', help='全量导入所有数据')
    parser.add_argument('--suppliers', action='store_true', help='只导入供应商')
    parser.add_argument('--projects', action='store_true', help='只导入项目')
    parser.add_argument('--orders', action='store_true', help='只导入订单')
    parser.add_argument('--payers', action='store_true', help='只导入付款单位')
    parser.add_argument('--pays', action='store_true', help='只导入付款单')
    parser.add_argument('--incremental', action='store_true', help='增量更新模式')
    
    args = parser.parse_args()
    
    # 默认全量导入
    if not any([args.all, args.suppliers, args.projects, args.orders, args.payers, args.pays]):
        args.all = True
    
    mode = 'incremental' if args.incremental else 'full'
    
    print("="*60)
    print("🚀 旧数据库一键导入工具")
    print("="*60)
    print(f"源文件: {SQL_FILE}")
    print(f"目标: {DB_FILE}")
    print(f"模式: {'增量更新' if mode == 'incremental' else '全量导入'}")
    print("-" * 60)
    
    content = read_sql_file()
    
    db_path = Path(DB_FILE)
    if not db_path.exists():
        print(f"❌ 错误: 找不到数据库 {DB_FILE}")
        sys.exit(1)
    
    conn = sqlite3.connect(db_path)
    
    try:
        if args.all or args.suppliers:
            import_suppliers(conn, content, mode)
        
        if args.all or args.payers:
            import_payers(conn, content, mode)

        if args.all or args.projects:
            import_projects(conn, content, mode)
        
        if args.all or args.orders:
            import_orders(conn, content, mode)
        
        if args.all or args.pays:
            import_pays(conn, content, mode)
        
        print_summary(conn)
        
    finally:
        conn.close()
    
    print("\n✅ 导入完成!")
    print("\n💡 后续操作:")
    print("  1. 用Navicat将数据传输到阿里云MySQL")
    print("  2. 在服务器执行: git pull && docker-compose restart web")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已取消")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
