
import re

def find_tables(filename):
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        
    tables = re.findall(r'CREATE TABLE `?(\w+)`?', content)
    print(f"Found tables: {tables}")
    
    for table in ['ums_project', 'core_file_info', 'base_project_info']:
        if table in tables:
            print(f"Found {table}!")
            # Find the definition
            start = content.find(f"CREATE TABLE `{table}`")
            if start == -1:
                 start = content.find(f"CREATE TABLE {table}")
            
            if start != -1:
                end = content.find(";", start)
                print(f"Definition for {table}:")
                print(content[start:end+1])
                print("-" * 20)

if __name__ == "__main__":
    find_tables("d:/pear_admin/pear-admin-flask/sf_db_prod20260206.sql")
