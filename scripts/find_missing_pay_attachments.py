
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Get DB config from environment
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "pear_admin")

db_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
engine = create_engine(db_url)

def find_missing():
    with engine.connect() as conn:
        print("Finding payments with fjid but no attachments...")
        
        # Get all payments with fjid
        query_all = text("SELECT id, pay_number, fjid FROM ums_pay WHERE fjid IS NOT NULL AND fjid != ''")
        all_pays = conn.execute(query_all).fetchall()
        
        # Get all payments with attachments
        query_done = text("SELECT id FROM ums_pay WHERE attachments IS NOT NULL AND attachments != '' AND attachments != '[]'")
        done_ids = set(row[0] for row in conn.execute(query_done).fetchall())
        
        missing = []
        for row in all_pays:
            if row[0] not in done_ids:
                missing.append(row)
        
        print(f"Total with fjid: {len(all_pays)}")
        print(f"Total done: {len(done_ids)}")
        print(f"Missing: {len(missing)}")
        
        print("-" * 20)
        print("Sample missing payments:")
        for m in missing[:20]:
            print(f"ID: {m[0]}, PayNum: {m[1]}, FJID: {m[2]}")

if __name__ == "__main__":
    find_missing()
