
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "pear_admin")

db_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
engine = create_engine(db_url)

SOURCE_SQL_FILE = "sf_db_prod20260206.sql"

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

def check_availability():
    # 1. Load available file IDs from dump
    print("Loading file IDs from dump...")
    available_ids = set()
    with open(SOURCE_SQL_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith("INSERT INTO `core_file_info`"):
                rows = split_sql_values(line[line.find("VALUES")+6:].strip())
                for row in rows:
                    if len(row) > 0:
                        available_ids.add(str(row[0]))
    print(f"Total available file IDs: {len(available_ids)}")

    # 2. Load fjids from DB
    print("Loading payment fjids from DB...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT fjid FROM ums_pay WHERE fjid IS NOT NULL AND fjid != ''"))
        pay_fjids = [str(r[0]) for r in result]
    print(f"Total payments with fjid: {len(pay_fjids)}")

    # 3. Compare
    found = 0
    missing = 0
    
    # Handle comma separated
    for pf in pay_fjids:
        ids = [x.strip() for x in pf.split(',')]
        # We consider "found" if at least one ID is found? Or all?
        # Let's count individual IDs
        for i in ids:
            if i in available_ids:
                found += 1
            else:
                missing += 1
                # print(f"Missing ID: {i}")

    print(f"Found IDs referenced in payments: {found}")
    print(f"Missing IDs referenced in payments: {missing}")

if __name__ == "__main__":
    check_availability()
