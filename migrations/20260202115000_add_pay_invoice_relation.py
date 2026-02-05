"""
添加付款单与发票关联表

Revision ID: 20260202115000
Create Date: 2026-02-02 11:50:00
"""

def upgrade():
    """升级数据库"""
    from pear_admin.extensions import db
    from sqlalchemy import text
    
    # 创建付款单与发票关联表
    with db.engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pay_invoice_relation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pay_id INTEGER NOT NULL,
                invoice_id INTEGER NOT NULL,
                create_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pay_id) REFERENCES ums_pay(id) ON DELETE CASCADE,
                FOREIGN KEY (invoice_id) REFERENCES material_invoice(id) ON DELETE CASCADE,
                UNIQUE(pay_id, invoice_id)
            )
        """))
        conn.commit()
    print("✓ 创建 pay_invoice_relation 表成功")


def downgrade():
    """降级数据库"""
    from pear_admin.extensions import db
    from sqlalchemy import text
    
    with db.engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS pay_invoice_relation"))
        conn.commit()
    print("✓ 删除 pay_invoice_relation 表成功")


if __name__ == "__main__":
    import sys
    import os
    
    # 添加项目根目录到 Python 路径
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from pear_admin import create_app
    
    app = create_app()
    with app.app_context():
        print("开始执行数据库迁移...")
        upgrade()
        print("数据库迁移完成!")
