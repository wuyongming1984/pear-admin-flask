
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

def inspect():
    with engine.connect() as conn:
        print("Inspecting ums_pay columns...")
        # Get columns
        columns_query = text("SHOW COLUMNS FROM ums_pay")
        columns = conn.execute(columns_query).fetchall()
        col_names = [c[0] for c in columns]
        print(f"Columns: {col_names}")
        
        has_fjid = 'fjid' in col_names
        has_pay_number = 'pay_number' in col_names
        has_fksqbh = 'fksqbh' in col_names
        
        print(f"Has fjid: {has_fjid}")
        print(f"Has pay_number: {has_pay_number}")
        print(f"Has fksqbh: {has_fksqbh}")
        
        if not has_fjid:
            print("fjid column missing! Cannot verify user claim directly.")
            return

        pay_col = 'pay_number' if has_pay_number else ('fksqbh' if has_fksqbh else 'id')
        
        print(f"Fetching samples with populated attachments (limit 20)...")
        query = text(f"SELECT {pay_col}, fjid, attachments FROM ums_pay WHERE attachments LIKE '%pay_attachments/%' LIMIT 20")
        result = conn.execute(query)
        count = 0
        for row in result:
            count += 1
            print(f"PAY: {row[0]}")
            print(f"  FJID: {row[1]}")
            print(f"  ATTS: {row[2][:150]}...")
            print("-" * 20)
        
        if count == 0:
            print("No payments with attachments found yet.")

if __name__ == "__main__":
    inspect()
