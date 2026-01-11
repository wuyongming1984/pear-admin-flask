from flask import Blueprint, Flask

from .attachment import attachment_api
from .department import department_api
from .order import order_api
from .passport import passport_api
from .pay import pay_api
from .project import project_api
from .rights import rights_api
from .role import role_api
from .supplier import supplier_api
from .upload import upload_api
from .user import user_api

def register_apis(app: Flask):
    apis = Blueprint("api", __name__, url_prefix="/api/v1")

    apis.register_blueprint(passport_api)
    apis.register_blueprint(rights_api)
    apis.register_blueprint(role_api)
    apis.register_blueprint(department_api)
    apis.register_blueprint(user_api)
    apis.register_blueprint(supplier_api)
    apis.register_blueprint(project_api)
    apis.register_blueprint(order_api)
    apis.register_blueprint(pay_api)
    apis.register_blueprint(upload_api)
    apis.register_blueprint(attachment_api)

    app.register_blueprint(apis)
