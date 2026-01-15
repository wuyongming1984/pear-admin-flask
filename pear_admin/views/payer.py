from flask import Blueprint, render_template

payer_bp = Blueprint("payer", __name__)


@payer_bp.get("/payer/info/payer_info.html")
def info():
    return render_template("payer/info/payer_info.html")
