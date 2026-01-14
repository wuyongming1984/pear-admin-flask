#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
供应商数据导入脚本 - MySQL版本（支持.env配置）
从旧数据库 sf_db_prod.sql 导入供应商数据到 ums_supplier 表（MySQL）
"""

import re
import pymysql
from datetime import datetime
from pathlib import Path
import sys
import os
from base64 import b64decode
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# 解密函数（根据您的加密方式调整）
def decrypt_password(encrypted_password, key=None):
    """
    尝试解密密码
    如果解密失败，返回原始字符串
    """
    try:
        # 如果是Base64编码的密文
        if encrypted_password.endswith('=='):
            # 这里需要根据实际的加密方式来实现
            # 暂时直接返回，让用户手动输入
            return None
        return encrypted_password
    except:
        return None


def load_mysql_config():
    """从.env文件加载MySQL配置"""
    env_file = Path(__file__).parent.parent / ".env"
    
    config = {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'database': 'pear_admin',
        'charset': 'utf8mb4'
    }
    
    if env_file.exists():
        print("📖 读取.env配置文件...")
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == 'MYSQL_ROOT_PASSWORD':
                        # 尝试解密
                        decrypted = decrypt_password(value)
                        if decrypted:
                            config['password'] = decrypted
                            print("✓ 从.env读取MySQL密码（加密）")
                        else:
                            print("⚠️  .env中的密码已加密，请手动输入")
                            config['password'] = None
                    elif key == 'MYSQL_DATABASE':
                        config['database'] = value
                        print(f"✓ 数据库名称: {value}")
    else:
        print("⚠️  未找到.env文件，使用默认配置")
    
    return config


def parse_insert_values(insert_line):
    """解析INSERT语句中的VALUES部分"""
    match = re.search(r"VALUES\s*\((.*?)\);", insert_line, re.DOTALL)
    if not match:
        return None
    
    values_str = match.group(1)
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
            field = ''.join(current).strip()
            values.append(field)
            current = []
        else:
            current.append(char)
        
        i += 1
    
    if current:
        field = ''.join(current).strip()
        values.append(field)
    
    return values


def clean_value(value):
    """清理字段值"""
    if value in ['null', 'NULL', '']:
        return None
    
    if value.startswith("'") and value.endswith("'"):
        value = value[1:-1]
    
    value = value.replace("\\'", "'")
    value = value.replace("\\r\\n", "\n")
    value = value.replace("\\n", "\n")
    
    return value.strip() if value else None


def convert_to_supplier_data(values):
    """将旧数据库的字段转换为新系统的字段"""
    if len(values) < 15:
        return None
    
    cleaned = [clean_value(v) for v in values]
    
    gysid, gyslx, gysmc, lxr, lxdh, khyh, yhzh = cleaned[0:7]
    ksrq, jsrq, bz, lrrydm, lrsj, xgrydm, xgsj, yxbz = cleaned[7:15]
    
    # 跳过无效记录
    if yxbz == '0':
        return None
    
    # 转换字段
    try:
        type_id = int(gyslx) if gyslx and gyslx in ['1', '2'] else 1
    except:
        type_id = 1
    
    name = gysmc[:128] if gysmc else '未命名供应商'
    contact_person = lxr if lxr else '未知'
    phone = lxdh.replace(' ', '') if lxdh and lxdh != '0' else '0'
    phone = phone[:32]
    bank_name = khyh if khyh and khyh != '0' else '-'
    bank_name = bank_name[:128]
    
    # 账号保存为字符串
    if yhzh and yhzh != '0':
        account_number = yhzh.strip()[:128]
    else:
        account_number = '0'
    
    # 转换时间
    if lrsj:
        try:
            create_at = datetime.strptime(lrsj, '%Y-%m-%d %H:%M:%S')
        except:
            create_at = datetime.now()
    else:
        create_at = datetime.now()
    
    return {
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


def import_suppliers(mysql_password=None):
    """执行导入"""
    print(f"\n{'='*60}")
    print(f"供应商数据导入工具（MySQL版本）")
    print(f"{'='*60}\n")
    
    # 加载配置
    mysql_config = load_mysql_config()
    
    # 如果配置中没有密码，使用传入的参数或提示输入
    if not mysql_config['password']:
        if mysql_password:
            mysql_config['password'] = mysql_password
        else:
            mysql_config['password'] = input("请输入MySQL root密码: ")
    
    # SQL文件路径
    sql_file = Path(__file__).parent.parent / "旧数据库sf_db_prod.sql"
    
    # 如果文件不存在，尝试从/tmp目录
    if not sql_file.exists():
        sql_file = Path("/tmp/旧数据库sf_db_prod.sql")
    
    print(f"SQL文件路径: {sql_file}")
    
    if not sql_file.exists():
        print(f"❌ SQL文件不存在")
        print(f"   请确保文件在以下位置之一：")
        print(f"   - {Path(__file__).parent.parent}/旧数据库sf_db_prod.sql")
        print(f"   - /tmp/旧数据库sf_db_prod.sql")
        return False
    
    # 读取SQL文件
    print("\n📖 读取SQL文件...")
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 提取INSERT语句
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
    
    # 连接MySQL
    print(f"\n💾 连接MySQL数据库 ({mysql_config['database']})...")
    try:
        conn = pymysql.connect(**mysql_config)
        cursor = conn.cursor()
        print("✓ 数据库连接成功")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        print(f"\n配置信息:")
        print(f"  Host: {mysql_config['host']}")
        print(f"  User: {mysql_config['user']}")
        print(f"  Database: {mysql_config['database']}")
        return False
    
    try:
        # 检查表是否存在
        cursor.execute("SHOW TABLES LIKE 'ums_supplier'")
        if not cursor.fetchone():
            print("❌ ums_supplier表不存在")
            return False
        
        # 检查并修改表结构
        print("\n🔧 检查表结构...")
        cursor.execute("DESCRIBE ums_supplier")
        columns = cursor.fetchall()
        
        account_col = None
        for col in columns:
            if col[0] == 'account_number':
                account_col = col[1]
                break
        
        if account_col:
            if b'bigint' in account_col.lower() if isinstance(account_col, bytes) else 'bigint' in str(account_col).lower():
                print("⚠️  检测到account_number为BIGINT类型，修改为VARCHAR...")
                try:
                    cursor.execute("ALTER TABLE ums_supplier MODIFY COLUMN account_number VARCHAR(128) NOT NULL COMMENT '银行账号'")
                    print("✓ 表结构已更新")
                except Exception as e:
                    print(f"⚠️  修改失败: {e}")
        
        # 清空现有数据
        print("\n⚠️  清空现有供应商数据...")
        cursor.execute("DELETE FROM ums_supplier")
        deleted_count = cursor.rowcount
        print(f"✓ 已删除 {deleted_count} 条旧记录")
        
        # 插入数据
        print("\n📥 开始导入数据...")
        success_count = 0
        error_count = 0
        error_details = []
        
        insert_sql = """
            INSERT INTO ums_supplier 
            (type_id, name, contact_person, phone, email, bank_name, 
             account_number, address, remark, create_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        for i, supplier in enumerate(suppliers, 1):
            try:
                cursor.execute(insert_sql, (
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
                
                if i % 100 == 0:
                    print(f"  进度: {i}/{len(suppliers)}")
                    
            except Exception as e:
                error_count += 1
                if error_count <= 3:
                    error_details.append(f"{supplier['name']}: {e}")
        
        # 显示错误详情
        if error_details:
            print(f"\n⚠️  导入错误示例：")
            for err in error_details:
                print(f"  - {err}")
        
        # 提交事务
        conn.commit()
        print("\n✓ 事务已提交")
        
        # 验证
        cursor.execute("SELECT COUNT(*) FROM ums_supplier")
        final_count = cursor.fetchone()[0]
        
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
        cursor.execute("SELECT id, name, contact_person, phone FROM ums_supplier LIMIT 5")
        rows = cursor.fetchall()
        
        if rows:
            print(f"\n📋 示例数据（前5条）：")
            print(f"{'ID':<5} {'供应商名称':<35} {'联系人':<15} {'电话':<20}")
            print(f"{'-'*80}")
            for row in rows:
                print(f"{row[0]:<5} {row[1]:<35} {row[2]:<15} {row[3]:<20}")
        
        print()
        return True
        
    except Exception as e:
        print(f"\n❌ 导入过程出错: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    # 从命令行参数获取MySQL密码
    mysql_pwd = sys.argv[1] if len(sys.argv) > 1 else None
    
    success = import_suppliers(mysql_pwd)
    sys.exit(0 if success else 1)
