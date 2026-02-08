
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
    print(f"Parsing {SOURCE_SQL_FILE} for file info...")
    
    file_map = {} # map fjid -> {fjdz, fjmc}
    
    with open(SOURCE_SQL_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # Parse core_file_info logic (same as before)
            if line.startswith("INSERT INTO `core_file_info`"):
                 rows = split_sql_values(line[line.find("VALUES")+6:].strip())
                 for row in rows:
                     # ID is 0, fjdz is 1, fjmc is 4
                     if len(row) >= 5:
                         fid = str(row[0])
                         fjdz = row[1]
                         fjmc = row[4]
                         file_map[fid] = {'fjdz': fjdz, 'fjmc': fjmc}
                         
    print(f"Found {len(file_map)} files details.")
    
    return file_map

def split_concatenated_ids(s, valid_ids):
    if not s: return []
    if s in valid_ids: return [s]
    
    # Try matching from the start with all possible lengths
    for i in range(1, len(s) + 1):
        prefix = s[:i]
        if prefix in valid_ids:
            remaining = s[i:]
            if not remaining:
                return [prefix]
            sub = split_concatenated_ids(remaining, valid_ids)
            if sub:
                return [prefix] + sub
    return [s] # Fallback to original if cannot split perfectly


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
    
    # Load file map from SQL dump
    file_map = parse_sql_dump()
    
    with app.app_context():
        # Get fjid mapping from DB raw sql
        from sqlalchemy import text
        print("Fetching fjid from ums_pay...")
        # Check if fjid column exists first (although verified)
        # Just assume it exists as per verifying step
        fjids_data = {}
        try:
            result = db.session.execute(text("SELECT id, fjid FROM ums_pay WHERE fjid IS NOT NULL AND fjid != ''"))
            for row in result:
                # row is (id, fjid)
                fjids_data[row[0]] = row[1]
            print(f"Loaded {len(fjids_data)} payments with fjid from DB.")
        except Exception as e:
            print(f"Error fetching fjid from DB: {e}")
            return

        # Iterate PayORM
        pays = PayORM.query.all()
        print(f"Scanning {len(pays)} payments in DB...")
        
        updated_count = 0
        
        for pay in pays:
            pay_num = pay.pay_number
            
            # Check if this payment has fjid in DB
            if pay.id in fjids_data:
                fjid_str = str(fjids_data[pay.id])
                
                # Handle comma separated AND concatenated IDs
                fjids_raw = [x.strip() for x in fjid_str.split(',') if x.strip()]
                fjids = []
                valid_ids = set(file_map.keys())
                for f in fjids_raw:
                    fjids.extend(split_concatenated_ids(f, valid_ids))
                
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
                # Identify expected files for this payment
                expected_files = [] 
                
                # Check valid IDs
                valid_ids_for_pay = []
                for fjid in fjids:
                    if fjid in file_map:
                        finfo = file_map[fjid]
                        valid_ids_for_pay.append(finfo)
                        expected_files.append(finfo['fjmc'])
                
                # Filter existing attachments
                # Keep manual uploads (not containing 'pay_attachments/') 
                # OR migration uploads that match expected files
                cleaned_attachments = []
                
                # Helper to check if url is a migration url
                def is_migration_url(url):
                    return 'pay_attachments/' in url

                for att in current_attachments:
                    if isinstance(att, dict):
                        url = att.get('url', '')
                        name = att.get('name', '')
                        
                        if is_migration_url(url):
                            # It's a migration file. Only keep if it matches one of our expected files
                            # Check by name is fuzzy but workable. Ideally check by content hash but hard.
                            # Or we can just re-add verified ones later and drop all old migration ones?
                            # Re-adding ensures URL is fresh.
                            # Let's drop ALL 'pay_attachments/' entries and let the loop below re-add them if valid.
                            pass
                        else:
                            cleaned_attachments.append(att)
                
                # Now append valid files (checking if we already have them in cleaned to avoid dupes? No, cleaned has no migration files)
                current_attachments = cleaned_attachments
                
                modified = True # We are rebuilding migration parts
                
                for fjid in fjids:
                    if fjid not in file_map:
                        print(f"  File ID {fjid} not found for Pay {pay_num}")
                        continue
                        
                    finfo = file_map[fjid]
                    fjdz = finfo['fjdz']
                    fjmc = finfo['fjmc']
                    
                    if not fjdz: 
                        continue
                    
                    # Download
                    if fjdz.startswith('http'):
                        full_url = fjdz
                    else:
                        full_url = LEGACY_FILE_BASE_URL + fjdz.lstrip('/')
                    
                    # Encode URL for special characters
                    from urllib.parse import urlparse, quote
                    p = urlparse(full_url)
                    full_url = f"{p.scheme}://{p.netloc}{quote(p.path)}"
                    if p.query:
                        full_url += f"?{p.query}"
                    
                    print(f"  Processing Pay {pay_num}: {fjmc} ({full_url})")
                    
                    try:
                        # Upload to /pay_attachments/
                        retries = 3
                        for attempt in range(retries):
                            try:
                                res = requests.get(full_url, timeout=30)
                                if res.status_code == 200:
                                    content = res.content
                                    content_type = res.headers.get('Content-Type')
                                    ext = os.path.splitext(fjmc)[1]
                                    if not ext:
                                        ext = os.path.splitext(fjdz)[1]
                                    if not ext:
                                        ext = ".bin"
                                        
                                    filename = f"pay_attachments/{uuid.uuid4().hex}{ext}"
                                    
                                    # Upload with explicit content type to avoid mimetypes hang on windows
                                    headers = {}
                                    if content_type:
                                        headers['Content-Type'] = content_type
                                    
                                    oss_utils.bucket.put_object(filename, content, headers=headers)
                                    
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
                                    break # Success
                                elif res.status_code == 503:
                                    print(f"    503 Service Unavailable, retrying ({attempt+1}/{retries})...")
                                    import time
                                    time.sleep(2 * (attempt + 1))
                                else:
                                    print(f"    Download failed: {res.status_code}")
                                    break # Other error, no retry
                            except requests.RequestException as e:
                                print(f"    Request error: {e}, retrying ({attempt+1}/{retries})...")
                                import time
                                time.sleep(2 * (attempt + 1))
                    except Exception as e:
                        print(f"    Error: {e}")
                
                if modified:
                    final_list = current_attachments + attachments_list
                    pay.attachments = json.dumps(final_list, ensure_ascii=False)
                    updated_count += 1
                    
                    if updated_count % 50 == 0:
                        db.session.commit()
                        print(f"  --- Batch commit: {updated_count} payments updated ---")
        
        db.session.commit()
        print(f"Migration complete. Updated {updated_count} payments.")

if __name__ == "__main__":
    migrate()
