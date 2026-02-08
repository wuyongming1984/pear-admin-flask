
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

def cleanup():
    with engine.connect() as conn:
        print("Starting cleanup of incorrect payment attachments...")
        
        # Identify records to clean
        # Criteria: fjid IS NULL/Empty AND attachments contains 'pay_attachments/'
        search_query = text("""
            SELECT id, pay_number, attachments 
            FROM ums_pay 
            WHERE (fjid IS NULL OR fjid = '') 
            AND attachments LIKE '%pay_attachments/%'
        """)
        
        to_clean = conn.execute(search_query).fetchall()
        print(f"Found {len(to_clean)} records to clean.")
        
        if not to_clean:
            print("No records found matching cleanup criteria.")
            return

        print("-" * 20)
        print("Sample records to be cleaned:")
        for r in to_clean[:5]:
            print(f"ID: {r[0]}, PayNum: {r[1]}")
        print("-" * 20)
        
        # Execute update
        print("Executing update...")
        update_query = text("""
            UPDATE ums_pay 
            SET attachments = NULL 
            WHERE (fjid IS NULL OR fjid = '') 
            AND attachments LIKE '%pay_attachments/%'
        """)
        
        result = conn.execute(update_query)
        conn.commit()
        
        print(f"Cleanup complete. Updated {result.rowcount} records.")

if __name__ == "__main__":
    cleanup()
