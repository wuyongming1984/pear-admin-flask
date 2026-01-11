from flask import Blueprint, render_template, send_from_directory
from flask_jwt_extended import jwt_required

supplier_bp = Blueprint("supplier", __name__)


# 数据库菜单配置的路由
@supplier_bp.route("/supplier/info/supplier_info.html")
def supplier_info():
    return render_template("supplier/info/supplier_info.html")





