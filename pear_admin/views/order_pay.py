from flask import Blueprint, render_template, send_from_directory
from flask_jwt_extended import jwt_required

order_pay_bp = Blueprint("order_pay", __name__)


# 数据库菜单配置的路由
@order_pay_bp.route("/order_pay/info/order_info.html")
def order_info():
    return render_template("order_pay/info/order_info.html")


@order_pay_bp.route("/order_pay/info/pay_info.html")
def pay_info():
    return render_template("order_pay/info/pay_info.html")


@order_pay_bp.route("/order_pay/base/order_base.html")
def order_base():
    return render_template("order_pay/order_base.html")


@order_pay_bp.route("/order_pay/base/pay_base.html")
def pay_base():
    return render_template("order_pay/pay_base.html")


