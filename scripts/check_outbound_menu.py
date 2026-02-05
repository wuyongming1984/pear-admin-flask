import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db
from sqlalchemy import text

app = create_app('dev')

def check_menu():
    with app.app_context():
        # Check for '拟出库计划' or route '/view/material/outbound'
        query = text("SELECT id, name, code, url FROM ums_rights WHERE name LIKE '%拟出库%' OR url LIKE '%/view/material/outbound%'")
        result = db.session.execute(query).fetchall()
        
        if result:
            print("Found menus:")
            for row in result:
                print(f"ID: {row[0]}, Name: {row[1]}, Code: {row[2]}, URL: {row[3]}")
        else:
            print("No menu found for Outbound Planning.")

if __name__ == "__main__":
    check_menu()
