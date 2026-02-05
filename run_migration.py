"""
运行付款单附件字段迁移
"""
import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db

app = create_app()

with app.app_context():
    with db.engine.connect() as conn:
        # 添加附件字段 (SQLite不支持COMMENT)
        conn.execute(db.text("""
            ALTER TABLE ums_pay 
            ADD COLUMN attachments TEXT NULL
        """))
        
        conn.commit()
    
    print("✓ 成功添加 attachments 字段到 ums_pay 表")
