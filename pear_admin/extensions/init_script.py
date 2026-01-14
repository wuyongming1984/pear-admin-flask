import csv
import os

from flask import Flask, current_app

from pear_admin.extensions import db
from pear_admin.orms import DepartmentORM, RightsORM, RoleORM, UserORM


def dict_to_orm(d, o):
    for k, v in d.items():
        if k == "password":
            o.password = v
        else:
            setattr(o, k, v or None)


def csv_to_databases(path, orm):
    with open(path, encoding="utf-8") as file:
        for d in csv.DictReader(file):
            o = orm()
            dict_to_orm(d, o)
            db.session.add(o)
            db.session.flush()
        db.session.commit()


def register_script(app: Flask):
    @app.cli.command()
    def init():
        from sqlalchemy import text, inspect

        # 检查关键表是否已存在（避免覆盖已导入的数据）
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        # 如果ums_supplier表已存在且有数据，跳过初始化
        if 'ums_supplier' in existing_tables:
            try:
                result = db.session.execute(text("SELECT COUNT(*) FROM ums_supplier")).scalar()
                if result > 10:  # 如果有超过10条记录，认为是用户导入的数据
                    print(f"✓ Database already initialized with {result} suppliers. Skipping initialization to preserve data.")
                    print("  If you want to reset: docker-compose down -v && docker-compose up -d")
                    return
            except:
                pass  # 如果查询失败，继续初始化

        print("Initializing fresh database...")
        
        # 1. 重置数据库结构
        db.drop_all()
        db.create_all()

        root = current_app.config.get("ROOT_PATH")
        sql_file_path = os.path.join(root, "static", "data", "databases.sql")

        # 2. 从 SQL 文件导入数据
        if os.path.exists(sql_file_path):
            print(f"Loading data from {sql_file_path}...")
            with open(sql_file_path, encoding="utf-8") as f:
                content = f.read()
                
                # 简单的 SQL 分割执行
                statements = content.split(';')
                for statement in statements:
                    statement = statement.strip()
                    if not statement:
                        continue
                        
                    # 跳过创建数据库和切换数据库的语句 (由 Docker 环境变量控制)
                    if statement.upper().startswith("CREATE DATABASE") or statement.upper().startswith("USE "):
                        continue
                        
                    try:
                        db.session.execute(text(statement))
                    except Exception as e:
                        print(f"Warning executing statement: {str(e)[:100]}...")
                
                db.session.commit()
                print("Data loaded successfully.")
        else:
            print(f"Warning: {sql_file_path} not found. Skipping data load.")

        # 旧的 CSV 导入逻辑已弃用，改用上面的 SQL 导入
        # ...

