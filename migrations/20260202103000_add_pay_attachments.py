"""
添加付款单附件字段

迁移时间: 20260202103000
"""

from pear_admin.extensions import db

def upgrade():
    """添加attachments字段到ums_pay表"""
    with db.engine.connect() as conn:
        # 添加附件字段
        conn.execute(db.text("""
            ALTER TABLE ums_pay 
            ADD COLUMN attachments TEXT NULL COMMENT '附件'
        """))
        
        conn.commit()
    
    print("✓ 成功添加 attachments 字段到 ums_pay 表")

def downgrade():
    """回滚：删除attachments字段"""
    with db.engine.connect() as conn:
        conn.execute(db.text("""
            ALTER TABLE ums_pay 
            DROP COLUMN attachments
        """))
        
        conn.commit()
    
    print("✓ 成功删除 ums_pay 表的 attachments 字段")

if __name__ == "__main__":
    print("执行数据库迁移...")
    upgrade()
    print("迁移完成!")
