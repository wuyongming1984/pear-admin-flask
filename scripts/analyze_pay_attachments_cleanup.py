
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import json

load_dotenv()

# Get DB config from environment
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "pear_admin")

db_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
engine = create_engine(db_url)

def analyze_cleanup():
    with engine.connect() as conn:
        print("Analyzing payments for cleanup...")
        
        # Criteria 1: fjid IS NULL/Empty BUT has attachments
        query = text("""
            SELECT id, pay_number, fjid, attachments 
            FROM ums_pay 
            WHERE (fjid IS NULL OR fjid = '') 
            AND attachments IS NOT NULL 
            AND attachments != '' 
            AND attachments != '[]'
        """)
        
        result = conn.execute(query).fetchall()
        
        candidates = []
        for row in result:
            att_str = row[3]
            # Check if it contains 'pay_attachments/' (indicator of our migration)
            if 'pay_attachments/' in att_str:
                candidates.append(row)
        
        print(f"Total records with fjid=NULL/Empty but populated attachments: {len(result)}")
        print(f"Records containing 'pay_attachments/' (likely migration artifacts): {len(candidates)}")
        
        if candidates:
            print("-" * 20)
            print("Sample candidates for cleanup:")
            for c in candidates[:10]:
                print(f"ID: {c[0]}, PayNum: {c[1]}, ATTS: {c[3][:100]}...")

if __name__ == "__main__":
    analyze_cleanup()
