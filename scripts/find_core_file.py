
import re

def find_core_file_info(filename):
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    table = "core_file_info"
    start = content.find(f"CREATE TABLE `{table}`")
    if start == -1:
         start = content.find(f"CREATE TABLE {table}")
    
    if start != -1:
        end = content.find(";", start)
        print(f"Definition for {table}:")
        print(content[start:end+1])
    else:
        print(f"Could not find definition for {table}")

if __name__ == "__main__":
    find_core_file_info("d:/pear_admin/pear-admin-flask/sf_db_prod20260206.sql")
