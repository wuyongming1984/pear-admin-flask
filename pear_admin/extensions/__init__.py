from flask import Flask

from .init_db import db, migrate
from .init_jwt import jwt
from .init_script import register_script
from .init_scheduler import scheduler, refresh_backup_scheduler_job
from pear_admin.oss_utils import OSSUtils

oss = OSSUtils()

def register_extensions(app: Flask):
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    oss.init_app(app)

    register_script(app)
    
    # 启用 APScheduler
    scheduler.init_app(app)
    scheduler.start()
    
    # 从数据库恢复系统层面的定时任务
    refresh_backup_scheduler_job(app)
