
def check_duplicates(file_path):
    targets = ['132']
    counts = {t: 0 for t in targets}
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith("INSERT INTO `core_file_info`"):
                # Simplified splitting for checking
                parts = line.split("VALUES (")
                if len(parts) > 1:
                    values_part = parts[1]
                    # This is rough, relying on the fact that ID is first
                    if values_part.startswith("132,"):
                        print(f"FOUND 132 RAW: {line[:200]}")
                        counts['132'] += 1

if __name__ == "__main__":
    check_duplicates('sf_db_prod20260206.sql')
