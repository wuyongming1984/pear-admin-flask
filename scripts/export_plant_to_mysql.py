import sqlite3
import os

# 数据库路径
db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'pear_admin.db')
output_file = os.path.join(os.path.dirname(__file__), '..', 'nursery_plant_data.sql')

def get_value_sql(val):
    if val is None:
        return 'NULL'
    if isinstance(val, str):
        return f"'{val}'"
    if isinstance(val, (int, float)):
        return str(val)
    return f"'{str(val)}'"

def export_plant_data():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        table_name = "nursery_plant"
        
        # 读取数据
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        # 获取列名
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        col_str = "`, `".join(columns)
        
        print(f"正在从本地导出 {len(rows)} 条库存记录...")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"-- 导出数据: {table_name}\n")
            f.write("USE pear_admin;\n")
            f.write(f"DROP TABLE IF EXISTS {table_name};\n")
            
            # MySQL 建表语句
            f.write(f"""
CREATE TABLE `{table_name}` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(100) NOT NULL COMMENT '苗木名称',
  `category` VARCHAR(50) COMMENT '分类',
  `spec` VARCHAR(100) COMMENT '规格',
  `unit` VARCHAR(20) COMMENT '单位',
  `quantity` DECIMAL(10, 2) DEFAULT 0 COMMENT '当前库存数量',
  `price` DECIMAL(10, 2) DEFAULT 0 COMMENT '加权平均成本价',
  `location` VARCHAR(100) COMMENT '存放位置',
  `remark` VARCHAR(255) COMMENT '备注',
  `create_at` DATETIME DEFAULT NULL COMMENT '创建时间',
  `update_at` DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

""")
            
            for row in rows:
                vals = [get_value_sql(val) for val in row]
                val_str = ", ".join(vals)
                sql = f"INSERT INTO `{table_name}` (`{col_str}`) VALUES ({val_str});\n"
                f.write(sql)
                
        print(f"导出成功！文件位置: {output_file}")
        print("请在 Navicat 中运行此 SQL 文件以修复库存数据。")
        
    except Exception as e:
        print(f"导出失败: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    export_plant_data()
