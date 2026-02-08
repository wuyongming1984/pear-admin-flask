
def list_pay_columns(sql_file):
    print(f"Reading schema from {sql_file}...")
    with open(sql_file, 'r', encoding='utf-8', errors='ignore') as f:
        in_table = False
        idx = 0
        for line in f:
            if "CREATE TABLE `core_payment_request_info`" in line:
                in_table = True
                print(f"FOUND TABLE: {line.strip()}")
                continue
            
            if in_table:
                line = line.strip()
                if line.startswith("`"):
                    col_name = line.split("`")[1]
                    print(f"{idx}: {col_name}")
                    idx += 1
                
                if ";" in line:
                    print("END TABLE")
                    break

if __name__ == "__main__":
    list_pay_columns('sf_db_prod20260206.sql')
