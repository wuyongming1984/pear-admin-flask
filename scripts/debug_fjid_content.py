
def split_sql_values(value_str):
    if value_str.endswith(';'): value_str = value_str[:-1]
    raw_rows = value_str.split("),(")
    rows = []
    for r in raw_rows:
        r = r.replace("(", "", 1).replace(")", "", 1) if r.startswith("(") else r.rstrip(")")
        parts = []
        current = ""
        in_quote = False
        escape = False
        for char in r:
            if char == "'" and not escape: in_quote = not in_quote; continue
            if char == "\\" and not escape: escape = True; continue
            if escape: escape = False; current += char; continue
            if char == "," and not in_quote: parts.append(current.strip()); current = ""
            else: current += char
        parts.append(current.strip())
        cleaned = []
        for p in parts:
            if p.upper() == 'NULL': cleaned.append(None)
            elif p.startswith("'") and p.endswith("'"): cleaned.append(p[1:-1])
            else: cleaned.append(p)
        rows.append(cleaned)
    return rows

def debug_ids(file_path):
    targets = ['132', '1324', '1338', '1140', '141']
    print(f"Searching for core_file_info IDs: {targets}")
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith("INSERT INTO `core_file_info`"):
                rows = split_sql_values(line[line.find("VALUES")+6:].strip())
                for row in rows:
                    # ID is index 0
                    if str(row[0]) in targets:
                        print(f"FOUND ID {row[0]}:")
                        print(f"  URL (fjdz): {row[1]}")
                        print(f"  Name (fjmc): {row[4]}")

if __name__ == "__main__":
    debug_ids('sf_db_prod20260206.sql')
