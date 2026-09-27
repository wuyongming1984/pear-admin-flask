from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
import json
from pear_admin.extensions import db
from pear_admin.orms.sys_config import SysConfigORM
import subprocess
import os
import sys

system_api = Blueprint("system_api", __name__, url_prefix="/system")

@system_api.get("/config/backup")
@jwt_required()
def get_backup_config():
    """获取备份配置"""
    config = db.session.scalar(db.select(SysConfigORM).where(SysConfigORM.key == 'backup_email_config'))
    
    data = {
        "mail_server": os.getenv("MAIL_SERVER", ""),
        "mail_port": os.getenv("MAIL_PORT", "465"),
        "mail_user": os.getenv("MAIL_USERNAME", ""),
        "mail_pass": os.getenv("MAIL_PASSWORD", ""),
        "mail_receiver": os.getenv("MAIL_RECEIVER", ""),
        "enable_auto_backup": False,
        "backup_time": "01:00"
    }
    
    if config and config.value:
        try:
            saved_data = json.loads(config.value)
            data.update(saved_data)
        except:
            pass
            
    # 脱敏密码
    if data["mail_pass"]:
        data["mail_pass"] = "******"
        
    return {"code": 0, "msg": "获取成功", "data": data}

@system_api.post("/config/backup")
@jwt_required()
def save_backup_config():
    """保存备份配置"""
    try:
        req_data = request.get_json(silent=True)
        if not isinstance(req_data, dict):
            return {"code": -1, "msg": "请提交有效配置"}
        req_data["enable_auto_backup"] = req_data.get("enable_auto_backup") in (True, "on", "true", 1)
        
        # 验证必填 (移除 mail_user)
        required = ["mail_server", "mail_port", "mail_receiver"]
        for r in required:
            if not req_data.get(r):
                return {"code": -1, "msg": f"{r} 不能为空"}
        
        # 获取现有配置
        config = db.session.scalar(db.select(SysConfigORM).where(SysConfigORM.key == 'backup_email_config'))
        
        if req_data.get("mail_pass") == "******":
            saved_data = json.loads(config.value) if config and config.value else {}
            req_data["mail_pass"] = saved_data.get("mail_pass") or os.getenv("MAIL_PASSWORD", "")
        try:
            port = int(req_data["mail_port"])
            if not 1 <= port <= 65535:
                raise ValueError()
        except (TypeError, ValueError):
            return {"code": -1, "msg": "邮箱端口必须为1至65535的整数"}
        import re
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", str(req_data.get("backup_time", "01:00"))):
            return {"code": -1, "msg": "备份时间格式应为HH:mm"}
        json_str = json.dumps(req_data)
        
        if config:
            config.value = json_str
            config.update_at = db.func.now()
        else:
            config = SysConfigORM(
                key='backup_email_config',
                value=json_str,
                description='数据库备份邮件配置'
            )
            db.session.add(config)
            
        db.session.commit()
        
        # 实时刷新调度任务
        from pear_admin.extensions.init_scheduler import refresh_backup_scheduler_job
        from flask import current_app
        refresh_backup_scheduler_job(current_app)
        
        return {"code": 0, "msg": "保存成功"}
    except Exception as e:
        db.session.rollback()
        return {"code": -1, "msg": str(e)}

@system_api.post("/backup/test")
@jwt_required()
def test_backup():
    """手动触发备份"""
    try:
        # 1. 检查配置
        config = db.session.scalar(db.select(SysConfigORM).where(SysConfigORM.key == 'backup_email_config'))
        if not config or not config.value:
            return {"code": -1, "msg": "请先保存配置"}
            
        conf_data = json.loads(config.value)
        
        # 2. 临时设置环境变量 (仅对子进程有效)
        env = os.environ.copy()
        # 优先使用配置中的值，如果没有则不设置（让脚本去读 .env）或者强制从当前环境读
        env['MAIL_SERVER'] = conf_data.get('mail_server', os.getenv("MAIL_SERVER"))
        env['MAIL_PORT'] = str(conf_data.get('mail_port', os.getenv("MAIL_PORT")))
        env['MAIL_RECEIVER'] = conf_data.get('mail_receiver')
        
        # 优先使用已保存的发送账号密码，空值回退到环境配置
        env['MAIL_USERNAME'] = conf_data.get('mail_user') or os.getenv("MAIL_USERNAME", "")
        env['MAIL_PASSWORD'] = conf_data.get('mail_pass') or os.getenv("MAIL_PASSWORD", "")
        
        # 3. 调用备份脚本
        script_path = os.path.join(os.getcwd(), 'scripts', 'backup_db.py')
        
        # Run process
        result = subprocess.run(
            [sys.executable, script_path],
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return {"code": 0, "msg": "备份并发送成功！日志：" + result.stdout}
        else:
            return {"code": -1, "msg": f"备份失败: {result.stderr} \n {result.stdout}"}
            
    except Exception as e:
        return {"code": -1, "msg": str(e)}
