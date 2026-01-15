import sys
import os
import sqlite3

# 连接数据库
conn = sqlite3.connect('instance/pear_admin.db')
cursor = conn.cursor()

# 检查 ums_pay 中的 payer_supplier_id 是否存在于 ums_payer
cursor.execute("""
    SELECT COUNT(*) 
    FROM ums_pay p
    LEFT JOIN ums_payer py ON p.payer_supplier_id = py.id
    WHERE p.payer_supplier_id IS NOT NULL AND py.id IS NULL
""")

invalid_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM ums_pay WHERE payer_supplier_id IS NOT NULL")
total_linked = cursor.fetchone()[0]

print(f"关联付款单位的付款单总数: {total_linked}")
print(f"无效关联数 (ID不在ums_payer中): {invalid_count}")

if invalid_count == 0 and total_linked > 0:
    print("✅ 验证成功：所有付款单位关联均有效")
else:
    print("❌ 验证失败：存在无效关联或无数据")

conn.close()
