import sys
import os
sys.path.append(os.getcwd())
from pear_admin import create_app
from pear_admin.extensions import db
from sqlalchemy import inspect

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    columns = inspector.get_columns('ums_order')
    print("Columns in ums_order table:")
    for column in columns:
        print(f"- {column['name']} ({column['type']})")
