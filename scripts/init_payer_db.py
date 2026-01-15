import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import PayerORM

app = create_app()

with app.app_context():
    print("正在创建 ums_payer 表...")
    db.create_all()
    print("创建完成！")
