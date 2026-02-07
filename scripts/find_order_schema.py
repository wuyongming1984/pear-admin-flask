
import re

def find_table_schema(filename, table_name):
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Try multiple patterns
    patterns = [
        f"CREATE TABLE `{table_name}`",
        f"CREATE TABLE {table_name}"
    ]
    
    start = -1
    for p in patterns:
        start = content.find(p)
        if start != -1:
            break
            
    if start != -1:
        end = content.find(";", start)
        print(f"Definition for {table_name}:")
        print(content[start:end+1])
    else:
        print(f"Could not find definition for {table_name}")

if __name__ == "__main__":
    find_table_schema("d:/pear_admin/pear-admin-flask/sf_db_prod20260206.sql", "core_order_info")
