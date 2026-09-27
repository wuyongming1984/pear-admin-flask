from ._system_validation import nested
from collections import OrderedDict
from copy import deepcopy

from flask import Blueprint, current_app, jsonify, make_response, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    jwt_required,
)

from pear_admin.extensions import db
from pear_admin.orms import UserORM

passport_api = Blueprint("passport", __name__)


@passport_api.post("/login")
def login_in():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("username"), str) or not isinstance(data.get("password"), str) or not data["username"].strip() or not data["password"]:
        return {"message": "请填写用户名和密码", "msg": "请填写用户名和密码", "code": -1}, 400

    user: UserORM = db.session.execute(
        db.select(UserORM).where(UserORM.username == data["username"])
    ).scalar()

    if not user:
        return {"message": "用户不存在", "code": -1}, 401
    if not user.check_password(data["password"]):
        return {"message": "用户密码错误", "code": -1}, 401

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)

    return jsonify({
        "code": 0,
        "msg": "登录成功",
        "access_token": access_token,
        "refresh_token": refresh_token,
    })


@passport_api.route("/logout", methods=["GET", "POST"])
@jwt_required()
def logout():
    return {"msg": "退出登录成功", "code": 0}


@passport_api.get("/menu")
@jwt_required()
def menus_api():
    try:
        rights_orm_list = set()
        current_user: UserORM = get_current_user()
        for role in current_user.role_list:
            for rights_orm in role.rights_list:
                if rights_orm.type != "auth":
                    rights_orm_list.add(rights_orm)

        items = sorted(rights_orm_list, key=lambda item: (item.sort or 0, item.id))
        return nested(items, lambda item: item.menu_json())
    except Exception:
        current_app.logger.exception("加载用户菜单失败")
        raise
