import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import RightsORM

config_name = os.getenv('FLASK_CONFIG', 'dev')
app = create_app(config_name)

def fix_menu_type():
    with app.app_context():
        # Fix: Change '苗木库存' from 'menu' type to 'path' type
        sub_menu = RightsORM.query.filter_by(code="nursery:inventory").first()
        if sub_menu:
            print(f"Before: type='{sub_menu.type}', url='{sub_menu.url}'")
            sub_menu.type = "path"  # 'path' means clickable link that opens in iframe
            db.session.commit()
            print(f"After: type='{sub_menu.type}', url='{sub_menu.url}'")
            print("Fixed! Please refresh the browser.")
        else:
            print("Menu 'nursery:inventory' not found.")

if __name__ == "__main__":
    fix_menu_type()
