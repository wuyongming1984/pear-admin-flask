
import re

def list_columns(filename, table_name):
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    start = content.find(f"CREATE TABLE `{table_name}`")
    if start == -1:
        print(f"Could not find table {table_name}")
        return

    end = content.find(";", start)
    table_def = content[start:end+1]
    
    # improved regex to find column names
    # `col_name` type ...
    columns = re.findall(r"`(\w+)`", table_def)
    print(f"Columns for {table_name}:")
    for i, col in enumerate(columns):
        print(f"{i}: {col}")

if __name__ == "__main__":
    list_columns("d:/pear_admin/pear-admin-flask/sf_db_prod20260206.sql", "core_order_info")
