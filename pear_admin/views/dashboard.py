from flask import Blueprint, render_template

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/view/dashboard/index.html")
def dashboard_index():
    return render_template("view/dashboard/index.html")
