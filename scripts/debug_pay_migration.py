
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import PayORM

app = create_app()

SOURCE_SQL_FILE = 'sf_db_prod20260206.sql'

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

def debug_migration():
    print(f"Parsing {SOURCE_SQL_FILE} for sample keys...")
    sql_keys = set()
    with open(SOURCE_SQL_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith("INSERT INTO `core_payment_request_info`"):
                values_part = line[line.find("VALUES")+6:].strip()
                rows = split_sql_values(values_part)
                for row in rows:
                    if len(row) > 1:
                        sql_keys.add(row[1]) # fksqbh
                        if len(sql_keys) >= 5: break
            if len(sql_keys) >= 5: break
            
    print(f"Sample SQL Keys (fksqbh): {list(sql_keys)}")

    with app.app_context():
        pays = PayORM.query.limit(5).all()
        db_keys = [p.pay_number for p in pays]
        print(f"Sample DB Keys (pay_number): {db_keys}")
            
if __name__ == "__main__":
    debug_migration()
