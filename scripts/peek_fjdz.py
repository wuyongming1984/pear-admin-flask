
import re

def peek_fjdz(filename):
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Simple regex to find INSERT INTO `core_file_info` ...
    # This is fragile for multi-line inserts but might work for a peek
    # SQL dump usually has INSERT INTO `table` VALUES (...);
    
    # let's try to find WHERE core_file_info data starts
    start = content.find("INSERT INTO `core_file_info`")
    if start != -1:
        print("Found data start")
        # Print next 1000 chars
        print(content[start:start+1000])
    else:
        print("No data found for core_file_info")

if __name__ == "__main__":
    peek_fjdz("d:/pear_admin/pear-admin-flask/sf_db_prod20260206.sql")
