from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, current_user
from flask import jsonify

def authorize(permission=None, log=False):
    """
    权限验证装饰器
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            
            # 如果是超级管理员(id=1)，直接通过
            if current_user.id == 1:
                return fn(*args, **kwargs)
                
            # 检查权限
            if permission:
                # 获取用户所有权限标识
                user_permissions = set()
                for role in current_user.role_list:
                    for right in role.rights_list:
                        if right.code:
                            user_permissions.add(right.code)
                            
                if permission not in user_permissions:
                    return jsonify({"code": 403, "msg": "没有权限执行此操作"}), 403
            
            # TODO: 实现日志记录
            if log:
                pass
                
            return fn(*args, **kwargs)
        return wrapper
    return decorator
