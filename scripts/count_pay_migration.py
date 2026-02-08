
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

def count_migrated():
    with engine.connect() as conn:
        print("Counting migrated payments...")
        query = text("SELECT COUNT(*) FROM ums_pay WHERE attachments IS NOT NULL AND attachments != '' AND attachments != '[]'")
        result = conn.execute(query).scalar()
        
        total_query = text("SELECT COUNT(*) FROM ums_pay WHERE fjid IS NOT NULL AND fjid != ''")
        total_with_fjid = conn.execute(total_query).scalar()
        
        print(f"Migrated: {result} / {total_with_fjid} (Target)")

if __name__ == "__main__":
    count_migrated()
