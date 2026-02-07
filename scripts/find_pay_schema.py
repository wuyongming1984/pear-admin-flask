
import re

def find_pay_schema(sql_file):
    print(f"Searching {sql_file} for ums_pay schema...")
    with open(sql_file, 'r', encoding='utf-8', errors='ignore') as f:
        in_table = False
        table_name = ""
        lines = []
        
        for line in f:
            if "CREATE TABLE" in line and "ums_pay" in line:
                in_table = True
                table_name = "ums_pay"
                print(f"Found table: {line.strip()}")
                lines.append(line.strip())
                continue
                
            if in_table:
                lines.append(line.strip())
                if ";" in line:
                    in_table = False
                    for l in lines:
                        print(l)
                    return

    print("ums_pay table not found.")

if __name__ == "__main__":
    find_pay_schema('sf_db_prod20260206.sql')
