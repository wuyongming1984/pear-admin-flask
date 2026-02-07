
import re

def list_tables(filename):
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    tables = re.findall(r'CREATE TABLE `?(\w+)`?', content)
    with open('tables_found.txt', 'w') as f_out:
        f_out.write('\n'.join(tables))
    print(f"Found {len(tables)} tables. Saved to tables_found.txt")

if __name__ == "__main__":
    list_tables("d:/pear_admin/pear-admin-flask/sf_db_prod20260206.sql")
