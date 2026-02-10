import pymysql
import sys
import os

# Add current directory to path to import configs
sys.path.append(os.getcwd())

from configs import config

# Need to set up a minimal Flask app context to access DB config if using SQLAlchemy, 
# but here I'll just use pymysql with the config directly for safety and simplicity.

# Load config
conf = config['dev'] 

# Parse SQLAlchemy URI
# mysql+pymysql://root:123456@127.0.0.1:3306/pear_admin
uri = conf.SQLALCHEMY_DATABASE_URI
parts = uri.replace('mysql+pymysql://', '').split('@')
user_pass = parts[0].split(':')
host_port_db = parts[1].split('/')
host_port = host_port_db[0].split(':')
db_name = host_port_db[1]

user = user_pass[0]
password = user_pass[1]
host = host_port[0]
port = int(host_port[1])
database = db_name

print(f"Connecting to {host}:{port}/{database} as {user}")

connection = pymysql.connect(
    host=host,
    user=user,
    password=password,
    database=database,
    port=port,
    cursorclass=pymysql.cursors.DictCursor
)

try:
    with connection.cursor() as cursor:
        # Check if columns exist
        cursor.execute("DESCRIBE ums_project")
        columns = [row['Field'] for row in cursor.fetchall()]
        
        new_columns = {
            'project_audit_price_amount': "DECIMAL(18, 2) COMMENT '审价金额'",
            'project_audit_amount': "DECIMAL(18, 2) COMMENT '审计金额'"
        }
        
        for col, definition in new_columns.items():
            if col not in columns:
                print(f"Adding column {col}...")
                sql = f"ALTER TABLE ums_project ADD COLUMN {col} {definition}"
                cursor.execute(sql)
                print(f"Column {col} added successfully.")
            else:
                print(f"Column {col} already exists. Skipping.")
        
    connection.commit()
    print("Migration completed successfully.")

except Exception as e:
    print(f"Error during migration: {e}")
    connection.rollback()
finally:
    connection.close()
