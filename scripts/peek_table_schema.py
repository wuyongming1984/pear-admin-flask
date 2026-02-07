
import re

def peek_table(sql_file, table_name):
    print(f"Peeking at table `{table_name}` in {sql_file}...")
    with open(sql_file, 'r', encoding='utf-8', errors='ignore') as f:
        in_table = False
        target_table = f"CREATE TABLE `{table_name}`"
        
        for line in f:
            if target_table in line:
                in_table = True
                print(line.strip())
                continue
                
            if in_table:
                print(line.strip())
                if ";" in line:
                    return

if __name__ == "__main__":
    peek_table('sf_db_prod20260206.sql', 'wym_cwfkxx')
    print("-" * 20)
    peek_table('sf_db_prod20260206.sql', 'core_payment_request_info')
