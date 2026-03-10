import os
import sys
import json
import subprocess
from flask_apscheduler import APScheduler
from pear_admin.orms.sys_config import SysConfigORM
from pear_admin.extensions.init_db import db

# 声明调度器实例
scheduler = APScheduler()

def run_backup_job():
    """定时执行备份的函数任务"""
    with scheduler.app.app_context():
        print("[Scheduler] 开始执行自动备份任务...")
        
        # 提取配置
        config = db.session.scalar(db.select(SysConfigORM).where(SysConfigORM.key == 'backup_email_config'))
        if not config or not config.value:
            print("[Scheduler] 未找到备份配置，取消执行。")
            return
            
        conf_data = json.loads(config.value)
        
        # 临时设置环境变量 (仅对子进程有效)
        env = os.environ.copy()
        
        env['MAIL_SERVER'] = conf_data.get('mail_server', os.getenv("MAIL_SERVER"))
        env['MAIL_PORT'] = str(conf_data.get('mail_port', os.getenv("MAIL_PORT")))
        env['MAIL_RECEIVER'] = conf_data.get('mail_receiver')
        env['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME", "")
        env['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD", "")
        
        # 调用备份脚本
        script_path = os.path.join(os.getcwd(), 'scripts', 'backup_db.py')
        
        # Run process
        result = subprocess.run(
            [sys.executable, script_path],
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("[Scheduler] 自动备份成功。")
            print(result.stdout)
        else:
            print(f"[Scheduler] 自动备份失败: {result.stderr}")

def refresh_backup_scheduler_job(app):
    """根据库里配置，更新（添加/修改/移除）定时调度任务"""
    with app.app_context():
        config = db.session.scalar(db.select(SysConfigORM).where(SysConfigORM.key == 'backup_email_config'))
        
        # 若之前配置了 task，先删除
        if scheduler.get_job("daily_backup_job"):
            scheduler.remove_job("daily_backup_job")
            
        if not config or not config.value:
            return
            
        conf_data = json.loads(config.value)
        enable = conf_data.get("enable_auto_backup", False)
        
        if enable:
            backup_time_str = conf_data.get("backup_time", "01:00")
            try:
                hour, minute = backup_time_str.split(":")
                scheduler.add_job(
                    id="daily_backup_job",
                    func=run_backup_job,
                    trigger="cron",
                    hour=int(hour),
                    minute=int(minute)
                )
                print(f"[Scheduler] 已设置每天 {backup_time_str} 执行自动备份任务")
            except Exception as e:
                print(f"[Scheduler] 解析执行时间错误: {e}")
