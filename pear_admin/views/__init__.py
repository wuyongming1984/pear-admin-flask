from flask import Flask

from .index import index_bp
from .system import system_bp
from .order_pay import order_pay_bp
from .supplier import supplier_bp
from .project import project_bp
from .payer import payer_bp


def register_views(app: Flask):
    app.register_blueprint(index_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(order_pay_bp)
    app.register_blueprint(supplier_bp)
    app.register_blueprint(project_bp)
    app.register_blueprint(payer_bp)