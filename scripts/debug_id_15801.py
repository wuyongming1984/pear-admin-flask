
def debug_id_15801(file_path):
    targets = ["(15801,"]
    print(f"Searching for ID 15801...")
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith("INSERT INTO `core_payment_request_info`"):
                if "VALUES (15801," in line:
                    print(f"FOUND 15801 RAW: {line[:300]}...")
            if line.startswith("INSERT INTO `core_file_info`"):
                 if "VALUES (132," in line:
                     print(f"FOUND FILE 132: {line[:300]}...")

if __name__ == "__main__":
    debug_id_15801('sf_db_prod20260206.sql')
