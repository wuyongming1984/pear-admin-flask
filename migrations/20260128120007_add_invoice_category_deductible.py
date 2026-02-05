"""
添加发票分类和抵扣字段

迁移时间: 20260128120007
"""

from pear_admin.extensions import db

def upgrade():
    """添加invoice_category和deductible字段到material_invoice表"""
    with db.engine.connect() as conn:
        # 添加发票大类字段
        conn.execute(db.text("""
            ALTER TABLE material_invoice 
            ADD COLUMN invoice_category VARCHAR(64) NULL COMMENT '发票大类'
        """))
        
        # 添加可否抵扣字段
        conn.execute(db.text("""
            ALTER TABLE material_invoice 
            ADD COLUMN deductible VARCHAR(64) NULL COMMENT '可否抵扣'
        """))
        
        conn.commit()
    
    print("✓ 成功添加 invoice_category 和 deductible 字段")

def downgrade():
    """回滚：删除invoice_category和deductible字段"""
    with db.engine.connect() as conn:
        conn.execute(db.text("""
            ALTER TABLE material_invoice 
            DROP COLUMN invoice_category,
            DROP COLUMN deductible
        """))
        
        conn.commit()
    
    print("✓ 成功删除 invoice_category 和 deductible 字段")

if __name__ == "__main__":
    print("执行数据库迁移...")
    upgrade()
    print("迁移完成！")
