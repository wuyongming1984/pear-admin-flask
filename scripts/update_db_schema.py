import sys
import os
import logging

# Add current directory to path
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from sqlalchemy import text, inspect
from sqlalchemy.dialects import mysql

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Force import of all ORMs to ensure they are registered with SQLAlchemy
from pear_admin import orms

# Explicitly use production config
app = create_app("prod")


def get_column_type_sql(column):
    """获取列的 SQL 类型定义"""
    try:
        # 尝试使用 MySQL 方言编译列类型
        col_type = column.type.compile(dialect=mysql.dialect())
        return col_type
    except:
        # 回退到通用类型
        type_name = str(column.type)
        return type_name


def get_column_definition(column):
    """获取完整的列定义 SQL"""
    col_type = get_column_type_sql(column)
    nullable = "" if column.nullable else " NOT NULL"
    default = ""
    if column.default is not None:
        if hasattr(column.default, 'arg'):
            default_val = column.default.arg
            if callable(default_val):
                default = ""  # 跳过函数默认值
            elif isinstance(default_val, str):
                default = f" DEFAULT '{default_val}'"
            else:
                default = f" DEFAULT {default_val}"
    
    return f"{col_type}{nullable}{default}"


def sync_table_columns(table_name, model_class, inspector, conn):
    """同步单个表的列结构"""
    logger.info(f"  检查表 '{table_name}'...")
    
    # 获取数据库中现有的列
    try:
        db_columns = {col['name']: col for col in inspector.get_columns(table_name)}
    except Exception as e:
        logger.warning(f"    无法获取表 '{table_name}' 的列信息: {e}")
        return
    
    # 获取 ORM 模型中定义的列
    model_columns = model_class.__table__.columns
    
    added_count = 0
    for column in model_columns:
        col_name = column.name
        
        if col_name not in db_columns:
            # 列不存在，需要添加
            col_def = get_column_definition(column)
            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}"
            
            logger.info(f"    添加列 '{col_name}': {col_def}")
            try:
                conn.execute(text(alter_sql))
                conn.commit()
                logger.info(f"    ✅ 成功添加列 '{col_name}'")
                added_count += 1
            except Exception as e:
                logger.error(f"    ❌ 添加列 '{col_name}' 失败: {e}")
    
    if added_count == 0:
        logger.info(f"    ✅ 表 '{table_name}' 结构已是最新")
    else:
        logger.info(f"    ✅ 表 '{table_name}' 添加了 {added_count} 个新列")


def migrate():
    logger.info("=" * 60)
    logger.info("开始数据库结构同步...")
    logger.info("=" * 60)
    
    with app.app_context():
        # Log which DB we are connecting to
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        # 隐藏密码
        if '@' in db_uri:
            safe_uri = db_uri.split('@')[-1]
            logger.info(f"连接到数据库: ...@{safe_uri}")
        else:
            logger.info(f"连接到数据库: {db_uri}")
        
        # Get connection
        conn = db.engine.connect()
        try:
            inspector = inspect(conn)
            existing_tables = inspector.get_table_names()
            
            # 1. 创建所有缺失的表
            logger.info("\n[步骤 1] 创建缺失的表...")
            db.create_all()
            
            # 重新获取表列表
            inspector = inspect(conn)
            new_tables = inspector.get_table_names()
            created_tables = set(new_tables) - set(existing_tables)
            if created_tables:
                for t in created_tables:
                    logger.info(f"  ✅ 新建表: {t}")
            else:
                logger.info("  ✅ 没有需要创建的新表")
            
            # 2. 遍历所有 ORM 模型，同步列结构
            logger.info("\n[步骤 2] 同步所有表的列结构...")
            
            # 获取所有已注册的模型
            models = db.Model.registry._class_registry.values()
            
            for model in models:
                # 跳过非表模型
                if not hasattr(model, '__tablename__'):
                    continue
                
                table_name = model.__tablename__
                
                # 检查表是否存在
                if table_name not in new_tables:
                    logger.warning(f"  ⚠️ 表 '{table_name}' 不存在于数据库中")
                    continue
                
                sync_table_columns(table_name, model, inspector, conn)
            
            logger.info("\n" + "=" * 60)
            logger.info("数据库结构同步完成!")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"同步失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()


if __name__ == "__main__":
    migrate()
