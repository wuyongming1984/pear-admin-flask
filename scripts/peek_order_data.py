
import re

def peek_order_data(filename):
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    start = content.find("INSERT INTO `core_order_info`")
    if start != -1:
        print("Found data start")
        print(content[start:start+500])
    else:
        print("No data found for core_order_info")

if __name__ == "__main__":
    peek_order_data("d:/pear_admin/pear-admin-flask/sf_db_prod20260206.sql")
