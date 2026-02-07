
import sys
import os
import re
import json
import requests
import mimetypes
import uuid
from datetime import datetime
from decimal import Decimal
import io
from urllib.parse import quote

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import PayORM
from pear_admin.oss_utils import OSSUtils

app = create_app()

SOURCE_SQL_FILE = 'sf_db_prod20260206.sql'
LEGACY_FILE_BASE_URL = "http://139.224.226.63/"

def parse_sql_dump():
    print(f"Parsing {SOURCE_SQL_FILE}...")
    
    pay_files = {} # map pay_number (fksqbh) -> fjid
    file_map = {} # map fjid -> {fjdz, fjmc}
    
    with open(SOURCE_SQL_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            
            # Parse wym_cwfkxx (Payment Table)
            # INSERT INTO `wym_cwfkxx` VALUES (..., 'fksqbh', ..., 'fjid', ...);
            if line.startswith("INSERT INTO `wym_cwfkxx`"):
                # Extract values content: (123, 'PAY001', ...)
                values_part = line[line.find("VALUES")+6:].strip()
                # Split by "), (" to handle multiple inserts if needed (dump usually one per line or block)
                # But mysql dump usually has one long value string, let's assume one line one insert or standard format
                
                # Regex to capture values is tricky. Let's do a simpler approach if format is consistent.
                # Assuming `fksqbh` is distinct enough.
                # Let's try to extract string values.
                
                parts = split_sql_values(values_part)
                for p in parts:
                    # Index check based on schema, but schema is huge.
                    # Let's rely on finding 'CW' or similar pattern for pay_number if index is unknown?
                    # Or better: `fksqbh` is usually index 1 (2nd col) or similar.
                    # wym_cwfkxx schema keys not fully known relative to index.
                    
                    # Wait, verify schema index from `peek_table_schema.py` output?
                    # Output showed create table. Let's assume:
                    # `fksqid` int (0)
                    # `fksqbh` varchar (1)
                    # ...
                    # `fjid` varchar (15) -- Found in previous analysis? 
                    # Actually peek output for wym_cwfkxx had `fjid`!
                    # `fjid` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '附件id',
                    
                    # We need the INDEX of fksqbh and fjid.
                    # Based on standard create table order, let's find them.
                    pass 
    
    # Re-reading schema to determine column indices
    columns = get_column_indices()
    fksqbh_idx = columns.get('fksqbh')
    fjid_idx = columns.get('fjid')
    
    if fksqbh_idx is None or fjid_idx is None:
        print("Could not find fksqbh or fjid column index.")
        return

    print(f"Column Mapping: fksqbh={fksqbh_idx}, fjid={fjid_idx}")

    count_pay = 0
    with open(SOURCE_SQL_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith("INSERT INTO `wym_cwfkxx`"):
                values_part = line[line.find("VALUES")+6:].strip()
                rows = split_sql_values(values_part)
                for row in rows:
                    if len(row) > max(fksqbh_idx, fjid_idx):
                        pay_num = row[fksqbh_idx]
                        fjid = row[fjid_idx]
                        
                        if pay_num and fjid and fjid != 'NULL':
                            pay_files[pay_num] = fjid
                            count_pay += 1

            # Parse core_file_info logic (same as before)
            if line.startswith("INSERT INTO `core_file_info`"):
                 rows = split_sql_values(line[line.find("VALUES")+6:].strip())
                 for row in rows:
                     # ID is 0, fjdz is 2, fjmc is 1 (based on previous script)
                     if len(row) >= 3:
                         fid = str(row[0])
                         fjmc = row[1]
                         fjdz = row[2]
                         file_map[fid] = {'fjdz': fjdz, 'fjmc': fjmc}
                         
    print(f"Found {len(pay_files)} payments with attachments.")
    print(f"Found {len(file_map)} files details.")
    
    return pay_files, file_map

def get_column_indices():
    cols = {}
    idx = 0
    with open(SOURCE_SQL_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        in_table = False
        for line in f:
            if "CREATE TABLE `wym_cwfkxx`" in line:
                in_table = True
                continue
            if in_table:
                line = line.strip()
                if line.startswith("`"):
                    col_name = line.split("`")[1]
                    cols[col_name] = idx
                    idx += 1
                if ";" in line:
                    break
    return cols

def split_sql_values(value_str):
    # Basic SQL value splitter - handles ('a', 1), ('b', 2)
    # Removing outer formatting
    if value_str.endswith(';'):
        value_str = value_str[:-1]
    
    # Split by "), ("
    # This is a naive split, assumes no "), (" inside strings. 
    # Valid enough for standard dump unless text contains it.
    raw_rows = value_str.split("),(")
    
    rows = []
    for r in raw_rows:
        r = r.replace("(", "", 1).replace(")", "", 1) if r.startswith("(") else r.rstrip(")")
        # Split by comma, respecting quotes
        # Using a simple regex or parser
        # For simplicity, let's use a quick parser
        parts = []
        current = ""
        in_quote = False
        escape = False
        
        for char in r:
            if char == "'" and not escape:
                in_quote = not in_quote
                continue
            if char == "\\" and not escape:
                escape = True
                continue
            if escape:
                escape = False
                current += char
                continue
            
            if char == "," and not in_quote:
                parts.append(current.strip())
                current = ""
            else:
                current += char
        parts.append(current.strip())
        
        # Clean nulls / quotes
        cleaned = []
        for p in parts:
            if p.upper() == 'NULL':
                cleaned.append(None)
            elif p.startswith("'") and p.endswith("'"):
                cleaned.append(p[1:-1])
            else:
                cleaned.append(p)
        rows.append(cleaned)
    return rows

def migrate():
    oss_utils = OSSUtils(app)
    if not oss_utils.bucket:
        print("OSS not configured!")
        return
        
    pay_files, file_map = parse_sql_dump()
    
    with app.app_context():
        # Iterate PayORM
        pays = PayORM.query.all()
        print(f"Scanning {len(pays)} payments in DB...")
        
        updated_count = 0
        
        for pay in pays:
            pay_num = pay.pay_number
            if pay_num in pay_files:
                fjid_str = pay_files[pay_num]
                
                # Handle comma separated
                fjids = [x.strip() for x in fjid_str.split(',') if x.strip()]
                
                attachments_list = []
                current_attachments = []
                
                # Check existing
                if pay.attachments:
                    try: 
                        current_attachments = json.loads(pay.attachments) if isinstance(pay.attachments, str) else pay.attachments
                    except: pass
                if not isinstance(current_attachments, list):
                    current_attachments = []
                
                # We append only new ones to avoid overwriting recent manual uploads?
                # The requirement says "add", implies overwrite or append.
                # Given migration context, usually populate empty.
                # Let's check duplicates by name?
                existing_names = set(a.get('name') for a in current_attachments if isinstance(a, dict))
                
                modified = False
                
                for fjid in fjids:
                    if fjid not in file_map:
                        print(f"  File ID {fjid} not found for Pay {pay_num}")
                        continue
                        
                    finfo = file_map[fjid]
                    fjdz = finfo['fjdz']
                    fjmc = finfo['fjmc']
                    
                    if not fjdz: 
                        continue
                        
                    if fjmc in existing_names:
                        continue
                        
                    # Download
                    full_url = LEGACY_FILE_BASE_URL + fjdz.lstrip('/')
                    print(f"  Processing Pay {pay_num}: {fjmc}")
                    
                    try:
                        # Upload to /pay_attachments/
                        res = requests.get(full_url, timeout=30)
                        if res.status_code == 200:
                            content = res.content
                            ext = os.path.splitext(fjmc)[1]
                            if not ext:
                                ext = os.path.splitext(fjdz)[1]
                            if not ext:
                                ext = ".bin"
                                
                            filename = f"pay_attachments/{uuid.uuid4().hex}{ext}"
                            
                            # Upload
                            # oss_utils.bucket.put_object(filename, content) 
                            # Better use internal method if possible or raw bucket
                            oss_utils.bucket.put_object(filename, content)
                            
                            # Construct URL
                            domain = oss_utils.bucket.endpoint.replace('http://', '').replace('https://', '')
                            new_url = f"https://{oss_utils.bucket.bucket_name}.{domain}/{filename}"
                            
                            attachments_list.append({
                                "name": fjmc,
                                "url": new_url,
                                "size": len(content)
                            })
                            modified = True
                            print(f"    Uploaded to {new_url}")
                        else:
                            print(f"    Download failed: {res.status_code}")
                    except Exception as e:
                        print(f"    Error: {e}")
                
                if modified:
                    final_list = current_attachments + attachments_list
                    pay.attachments = json.dumps(final_list, ensure_ascii=False)
                    updated_count += 1
        
        if updated_count > 0:
            db.session.commit()
            print(f"Migration complete. Updated {updated_count} payments.")
        else:
            print("No updates needed.")

if __name__ == "__main__":
    migrate()
