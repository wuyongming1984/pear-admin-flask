from flask import Blueprint, render_template

nursery_bp = Blueprint("nursery", __name__)

@nursery_bp.get("/nursery/inventory")
def inventory():
    """苗圃库存列表页"""
    return render_template("nursery/inventory.html")

@nursery_bp.get("/nursery/transactions")
def transactions():
    """苗圃流水列表页"""
    return render_template("nursery/history.html")

@nursery_bp.get("/nursery/inbound")
def inbound():
    """入库登记页面"""
    return render_template("nursery/inbound.html")

@nursery_bp.get("/nursery/outbound")
def outbound():
    """出库管理页面"""
    return render_template("nursery/outbound.html")

@nursery_bp.get("/nursery/dashboard")
def dashboard():
    """仪表盘页面"""
    return render_template("nursery/dashboard.html")

@nursery_bp.get("/nursery/orders")
def orders():
    """出库单管理页面"""
    return render_template("nursery/orders.html")

@nursery_bp.get("/nursery/logs")
def logs():
    """操作日志页面"""
    return render_template("nursery/logs.html")

@nursery_bp.get("/nursery/settings")
def settings():
    """基础数据管理页面"""
    return render_template("nursery/settings.html")


