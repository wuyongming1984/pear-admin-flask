"""change_order_project_name_to_project_id

Revision ID: 0b63714f2895
Revises: f3e0d709c462
Create Date: 2026-02-02 02:05:24.176267

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0b63714f2895'
down_revision = 'f3e0d709c462'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: 添加新的 project_id 列
    with op.batch_alter_table('ums_order', schema=None) as batch_op:
        batch_op.add_column(sa.Column('project_id', sa.Integer(), nullable=True, comment='项目ID'))
    
    # Step 2: 数据迁移 - 通过 project_name 匹配并填充 project_id
    connection = op.get_bind()
    
    # 获取所有订单的 project_name 和对应的 project id
    result = connection.execute(sa.text("""
        UPDATE ums_order 
        SET project_id = (
            SELECT id FROM ums_project 
            WHERE ums_project.project_name = ums_order.project_name
        )
        WHERE project_name IS NOT NULL
    """))
    
    # 记录无法匹配的项目名称（用于排查）
    orphan_records = connection.execute(sa.text("""
        SELECT DISTINCT project_name 
        FROM ums_order 
        WHERE project_name IS NOT NULL 
        AND project_id IS NULL
    """)).fetchall()
    
    if orphan_records:
        print(f"⚠️  警告: 以下项目名称无法在 ums_project 表中找到匹配:")
        for record in orphan_records:
            print(f"   - {record[0]}")
    
    # Step 3: 删除旧的 project_name 列
    with op.batch_alter_table('ums_order', schema=None) as batch_op:
        batch_op.drop_column('project_name')
    
    # Step 4: 添加外键约束
    with op.batch_alter_table('ums_order', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_order_project_id',
            'ums_project',
            ['project_id'],
            ['id'],
            ondelete='SET NULL'
        )


def downgrade():
    # Step 1: 删除外键约束
    with op.batch_alter_table('ums_order', schema=None) as batch_op:
        batch_op.drop_constraint('fk_order_project_id', type_='foreignkey')
    
    # Step 2: 添加回 project_name 列
    with op.batch_alter_table('ums_order', schema=None) as batch_op:
        batch_op.add_column(sa.Column('project_name', sa.String(length=128), nullable=True, comment='项目名称'))
    
    # Step 3: 数据回填 - 从 project_id 关联获取 project_name
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE ums_order 
        SET project_name = (
            SELECT project_name FROM ums_project 
            WHERE ums_project.id = ums_order.project_id
        )
        WHERE project_id IS NOT NULL
    """))
    
    # Step 4: 删除 project_id 列
    with op.batch_alter_table('ums_order', schema=None) as batch_op:
        batch_op.drop_column('project_id')

