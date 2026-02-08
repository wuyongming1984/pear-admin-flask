
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

with engine.connect() as conn:
    print("Checking ID for F-20230628140101...")
    result = conn.execute(text("SELECT id FROM ums_pay WHERE pay_number = 'F-20230628140101'")).scalar()
    print(f"ID is: {result}")
