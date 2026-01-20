import sqlite3
import os
import datetime

# 数据库路径
db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'pear_admin.db')
output_file = os.path.join(os.path.dirname(__file__), '..', 'nursery_data.sql')

def get_value_sql(val):
    if val is None:
        return 'NULL'
    if isinstance(val, str):
        return f"'{val}'"
    if isinstance(val, (int, float)):
        return str(val)
    return f"'{str(val)}'"

def export_data():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 读取数据
        cursor.execute("SELECT * FROM nursery_transaction")
        rows = cursor.fetchall()
        
        # 获取列名
        cursor.execute("PRAGMA table_info(nursery_transaction)")
        columns = [col[1] for col in cursor.fetchall()]
        col_str = "`, `".join(columns)
        
        print(f"正在从本地导出 {len(rows)} 条记录...")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("-- 导出数据: nursery_transaction\n")
            f.write("USE pear_admin;\n")
            f.write("DROP TABLE IF EXISTS nursery_transaction;\n")
            f.write("""
CREATE TABLE `nursery_transaction` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `order_no` VARCHAR(50) NOT NULL,
  `type` VARCHAR(10) NOT NULL,
  `plant_id` INT NULL,
  `plant_name` VARCHAR(100) NULL,
  `spec` VARCHAR(100) NULL,
  `unit` VARCHAR(20) NULL,
  `quantity` DECIMAL(10,2) NOT NULL,
  `price` DECIMAL(10,2) NULL,
  `total_price` DECIMAL(12,2) NULL,
  `operator` VARCHAR(50) NULL,
  `destination` VARCHAR(100) NULL,
  `location` VARCHAR(100) NULL,
  `remark` VARCHAR(255) NULL,
  `create_at` DATETIME NULL,
  PRIMARY KEY (`id`),
  INDEX `ix_nursery_transaction_order_no` (`order_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

""")
            # f.write("TRUNCATE TABLE nursery_transaction;\n\n") # 不需要 truncate 了，直接重建
            
            for row in rows:
                vals = [get_value_sql(val) for val in row]
                val_str = ", ".join(vals)
                sql = f"INSERT INTO `nursery_transaction` (`{col_str}`) VALUES ({val_str});\n"
                f.write(sql)
                
        print(f"导出成功！文件位置: {output_file}")
        print("请在 Navicat 中打开此文件并执行，或者在服务器运行它。")
        
    except Exception as e:
        print(f"导出失败: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    export_data()
