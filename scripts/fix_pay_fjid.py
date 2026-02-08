import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms.pay import PayORM
from dotenv import load_dotenv

load_dotenv()

# Setup Flask app context
app = create_app("prod")

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

def parse_payment_fjid():
    print(f"Parsing {SOURCE_SQL_FILE} to extract correct fjid...")
    
    pay_fjid_map = {} # map new_pay_number -> fjid (or None)
    
    with open(SOURCE_SQL_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith("INSERT INTO `core_payment_request_info`"):
                values_part = line[line.find("VALUES")+6:].strip()
                rows = split_sql_values(values_part)
                for row in rows:
                    # Index based on analysis:
                    # 1: fksqbh
                    # 7: fjid
                    if len(row) > 7:
                        pay_num = row[1]
                        fjid = row[7]
                        
                        if pay_num:
                            # Transform old ID to new ID format: S-... -> F-...01
                            new_pay_num = pay_num
                            if pay_num.startswith('S'):
                                new_pay_num = 'F' + pay_num[1:] + '01'
                            
                            # Normalize fjid
                            if fjid == 'NULL' or fjid == '0': # observed '0' in some empty looking fields?
                                fjid = None
                            if not fjid:
                                fjid = None
                                
                            pay_fjid_map[new_pay_num] = fjid

    print(f"Extracted mappings for {len(pay_fjid_map)} payments.")
    return pay_fjid_map

def fix_fjid():
    pay_fjid_map = parse_payment_fjid()
    
    with app.app_context():
        print("Starting batch update of ums_pay.fjid...")
        
        pays = PayORM.query.all()
        print(f"Total payments in DB: {len(pays)}")
        
        updates = 0
        cleared = 0
        
        for pay in pays:
            pay_num = pay.pay_number
            
            # Logic: If we have a map entry, rely on it.
            # If map entry says fjid is None, we set DB to None.
            # If map entry has value, we set DB to value.
            # If pay_number NOT in map? Keep as is? Or warn?
            # Given we are fixing, likely the DB records came from this import.
            
            if pay_num in pay_fjid_map:
                correct_fjid = pay_fjid_map[pay_num]
                
                # Check mismatch
                current_fjid = pay.fjid
                
                # Update if different
                # Treat empty string as None for comparison
                if not current_fjid: current_fjid = None
                
                if str(current_fjid) != str(correct_fjid) and (current_fjid is not None or correct_fjid is not None):
                    # print(f"Fixing {pay_num}: {current_fjid} -> {correct_fjid}")
                    pay.fjid = correct_fjid
                    updates += 1
                    if not correct_fjid:
                        cleared += 1
            else:
                # If not in map, maybe manually creating? Leave it.
                pass
        
        db.session.commit()
        print(f"Correction complete.")
        print(f"Total records updated: {updates}")
        print(f"Records where fjid was cleared (set to NULL): {cleared}")

if __name__ == "__main__":
    fix_fjid()
