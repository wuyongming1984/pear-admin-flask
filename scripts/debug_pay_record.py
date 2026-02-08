
def debug_pay_record(file_path):
    targets = ["②吴32.3-158", "②吴32.4-159"]
    print(f"Searching for payments {targets}...")
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith("INSERT INTO `core_payment_request_info`"):
                parts = line.split("VALUES (")
                for p in parts[1:]:
                    for t in targets:
                        if t in p:
                            print(f"FOUND {t}:")
                            # Try to extract the whole value tuple
                            # It ends with ); or ),(
                            end_idx = p.find(")")
                            val_str = p[:end_idx]
                            # Split by comma respecting quotes is hard, but we know fjid position roughly
                            # Let's just print the raw string to be safe
                            print(f"  RAW: {val_str}")
                        
if __name__ == "__main__":
    debug_pay_record('sf_db_prod20260206.sql')
