
import os
import sys
import re
import json
import requests
import mimetypes
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import ProjectORM, AttachmentORM
from pear_admin.oss_utils import OSSUtils

app = create_app()

SQL_DUMP_PATH = "d:/pear_admin/pear-admin-flask/sf_db_prod20260206.sql"

def parse_sql_values(line):
    """
    Rudimentary SQL VALUES parser.
    Assumes values are in (val1, 'val2', ...), (...) format.
    This is not a full SQL parser but good enough for standard mysqldump structure.
    """
    # Remove INSERT INTO ... VALUES
    content = line[line.find("VALUES") + 6:].strip()
    if content.endswith(";"):
        content = content[:-1]
    
    # Split by ), ( to separate records
    # This acts as a generator
    current_record = ""
    in_quote = False
    
    for char in content:
        if char == '(' and not in_quote:
            current_record = ""
            continue
        elif char == ')' and not in_quote:
            # Process record
            yield parse_record_str(current_record)
            current_record = ""
        elif char == "'" and current_record and current_record[-1] != '\\':
            in_quote = not in_quote
            current_record += char
        else:
            current_record += char

def parse_record_str(record_str):
    """
    Parses a single record string like "1, 'name', NULL, '2023-01-01'"
    """
    values = []
    current_val = ""
    in_quote = False
    
    for i, char in enumerate(record_str):
        if char == "'" and (i == 0 or record_str[i-1] != '\\'):
            in_quote = not in_quote
            continue # Don't keep quotes
        
        if char == ',' and not in_quote:
            val = current_val.strip()
            if val == "NULL":
                values.append(None)
            else:
                values.append(val)
            current_val = ""
        else:
            current_val += char
            
    # Last value
    val = current_val.strip()
    if val == "NULL":
        values.append(None)
    else:
        values.append(val)
        
    return values

def load_source_data():
    print(f"Reading SQL dump from {SQL_DUMP_PATH}...")
    
    projects = {} # xmmc -> {xmid, fjid_str}
    files = {}    # fjid -> {url, name}
    
    with open(SQL_DUMP_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith("INSERT INTO `base_project_info`"):
                # Table structure: 
                # xmid(0), xmmc(1), xmjc(2), xmgm(3), ksrq(4), jsrq(5), xmzt(6), xmje(7), fjid(8), ...
                # Based on create table statement seen earlier
                # `xmid` int NOT NULL AUTO_INCREMENT COMMENT '项目id',
                # `xmmc` varchar(200) ...
                # ...
                # `fjid` varchar(500) ...
                
                # Careful with simple splitting if strings contain comma
                # My manual parser above is safer but slow. 
                # For this task, let's use a simpler approach since we know the structure might be simple enough 
                # or use regex for the specific fields we need.
                
                # Let's try to extract specifically using regex to be safer for the specific INSERT format
                # INSERT INTO `base_project_info` VALUES (6, '19泡泡公园', ...
                
                parts = line.split("VALUES", 1)
                if len(parts) < 2: continue
                
                val_part = parts[1].strip().rstrip(";")
                # Quick hack: create a list of records
                records = re.findall(r"\(([^)]+)\)", val_part)
                for rec in records:
                    # This split is dangerous if value contains comma.
                    # Use a CSV reader property if possible or smart split
                    # Given the constraints, let's try to split by ',' respecting quotes
                    vals = [x.strip().strip("'") for x in re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", rec)]
                    
                    if len(vals) >= 9:
                        xmmc = vals[1]
                        fjid = vals[8]
                        if fjid and fjid != 'NULL' and fjid != '':
                            projects[xmmc] = fjid
                            
            elif line.startswith("INSERT INTO `core_file_info`"):
                # `fjid` int NOT NULL AUTO_INCREMENT COMMENT '附件id',
                # `fjdz` varchar(500) ... COMMENT '附件地址',
                # `fkdwid` varchar(200) ... (skipped)
                # `gyslx` ...
                # ...
                # `fjmc` varchar(500) ...
                
                # We need column indices. 
                # Based on previous GREP:
                # `fjid` int, `fjdz` varchar, ... `fjmc` varchar
                # Let's peek at one insert to be sure of order
                # INSERT INTO `core_file_info` VALUES (98, 'http://...', '123..', '材料', 'e9f...', ...)
                # 0: fjid
                # 1: fjdz
                # 2: ...
                # 3: ...
                # 4: fjmc
                
                parts = line.split("VALUES", 1)
                if len(parts) < 2: continue
                val_part = parts[1].strip().rstrip(";")
                records = re.findall(r"\(([^)]+)\)", val_part)
                for rec in records:
                    vals = [x.strip().strip("'") for x in re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", rec)]
                    if len(vals) >= 5:
                        f_id = vals[0]
                        url = vals[1]
                        name = vals[4]
                        files[f_id] = {"url": url, "name": name}

    print(f"Loaded {len(projects)} projects with potential attachments.")
    print(f"Loaded {len(files)} file records.")
    return projects, files

def download_file(url):
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.content, response.headers.get('Content-Type')
    except Exception as e:
        print(f"Error downloading {url}: {e}")
    return None, None

def migrate():
    source_projects, source_files = load_source_data()
    
    oss_utils = OSSUtils(app)
    if not oss_utils.bucket:
        print("OSS not configured! Aborting.")
        return

    with app.app_context():
        # Get all target projects
        target_projects = ProjectORM.query.all()
        print(f"Found {len(target_projects)} projects in target DB.")
        
        updated_count = 0
        
        for project in target_projects:
            if project.project_name in source_projects:
                fjid_str = source_projects[project.project_name]
                fjids = [x.strip() for x in fjid_str.split(',') if x.strip()]
                
                print(f"Processing '{project.project_name}' (ID: {project.id}). Found {len(fjids)} attachments in source.")
                
                new_attachments_list = []
                
                for fjid in fjids:
                    if fjid in source_files:
                        file_info = source_files[fjid]
                        url = file_info['url']
                        original_name = file_info['name']
                        
                        print(f"  - Downloading {original_name} from {url}...")
                        content, content_type = download_file(url)
                        
                        if content:
                            # Create a file-like object
                            from io import BytesIO
                            file_stream = BytesIO(content)
                            
                            # Guess extension if not present
                            if '.' not in original_name:
                                ext = mimetypes.guess_extension(content_type) or '.bin'
                                filename = f"{original_name}{ext}"
                            else:
                                filename = original_name
                            
                            # Determine internal filename
                            import uuid
                            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'bin'
                            internal_filename = f"{uuid.uuid4().hex}.{ext}"
                            
                            # Helper to mock FileStorage-like behavior or just modify OSSUtils to accept bytes/stream
                            # OSSUtils.upload_file expects a standard Flask FileStorage or something with .read(), .seek() and .mimetype
                            
                            class MockFileStorage:
                                def __init__(self, stream, filename, mimetype):
                                    self.stream = stream
                                    self.filename = filename
                                    self.mimetype = mimetype
                                def read(self, size=-1):
                                    return self.stream.read(size)
                                def seek(self, offset, whence=0):
                                    return self.stream.seek(offset, whence)
                                def tell(self):
                                    return self.stream.tell()

                            mock_file = MockFileStorage(file_stream, internal_filename, content_type)
                            
                            try:
                                print(f"    Uploading {internal_filename} to OSS...")
                                # We need to use put_object directly or adapt upload_file
                                # oss_utils.upload_file(mock_file, internal_filename)
                                # Let's use the public method
                                oss_url = oss_utils.upload_file(mock_file, internal_filename)
                                
                                if oss_url:
                                    print(f"    Success: {oss_url}")
                                    
                                    # Create AttachmentORM
                                    # attachment_code? maybe random or sequential
                                    import random
                                    from datetime import datetime as dt
                                    code = f"ATT-{int(dt.now().timestamp())}-{random.randint(1000,9999)}"
                                    
                                    attachment = AttachmentORM(
                                        project_id=project.id,
                                        attachment_code=code,
                                        filename=internal_filename,
                                        original_filename=original_name,
                                        file_path=oss_url,
                                        file_size=len(content)
                                    )
                                    db.session.add(attachment)
                                    
                                    new_attachments_list.append({
                                        "name": original_name,
                                        "url": oss_url,
                                        "size": len(content)
                                    })
                                else:
                                    print("    Failed to get OSS URL.")
                                    
                            except Exception as e:
                                print(f"    Upload failed: {e}")
                        else:
                            print("    Download failed.")
                    else:
                        print(f"  - File ID {fjid} not found in file info.")
                
                # Update project.attachments json
                if new_attachments_list:
                    current_attachments = []
                    # Try to load existing
                    if project.attachments:
                        try:
                            current_attachments = json.loads(project.attachments)
                        except:
                            current_attachments = []
                    
                    # Merge? Or just append?
                    # The users request implies "add", so let's append
                    current_attachments.extend(new_attachments_list)
                    
                    project.attachments = json.dumps(current_attachments, ensure_ascii=False)
                    updated_count += 1
            
        db.session.commit()
        print(f"Migration complete. Updated {updated_count} projects.")

if __name__ == "__main__":
    migrate()
