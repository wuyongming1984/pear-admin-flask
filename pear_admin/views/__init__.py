from flask import Flask

from .index import index_bp
from .system import system_bp
from .order_pay import order_pay_bp
from .supplier import supplier_bp
from .project import project_bp
from .payer import payer_bp
from .dictionary import dictionary_bp
from .dashboard import dashboard_bp
from .nursery import nursery_bp
from .material import material_bp


def register_views(app: Flask):
    app.register_blueprint(index_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(order_pay_bp)
    app.register_blueprint(supplier_bp)
    app.register_blueprint(project_bp)
    app.register_blueprint(payer_bp)
    app.register_blueprint(dictionary_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(nursery_bp)
    app.register_blueprint(material_bp)
    
    # Import from apis to keep logic grouped, even though it renders views
    from pear_admin.apis.portal import portal_bp
    app.register_blueprint(portal_bp)