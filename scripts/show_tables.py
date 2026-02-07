
def list_tables(sql_file):
    print(f"Scanning {sql_file} for tables...")
    with open(sql_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if "CREATE TABLE" in line:
                print(line.strip())

if __name__ == "__main__":
    list_tables('sf_db_prod20260206.sql')
