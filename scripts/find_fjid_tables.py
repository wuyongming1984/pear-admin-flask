
def find_fjid_tables(sql_file):
    print(f"Scanning {sql_file} for tables with `fjid`...")
    with open(sql_file, 'r', encoding='utf-8', errors='ignore') as f:
        current_table = ""
        in_table = False
        
        for line in f:
            if "CREATE TABLE" in line:
                current_table = line.strip()
                in_table = True
                continue
                
            if in_table:
                if "`fjid`" in line:
                    print(f"Found `fjid` in: {current_table}")
                
                if ";" in line:
                    in_table = False
                    current_table = ""

if __name__ == "__main__":
    find_fjid_tables('sf_db_prod20260206.sql')
