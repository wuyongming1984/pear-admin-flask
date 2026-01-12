from flask import Flask, render_template

from configs import config
from pear_admin.apis import register_apis
from pear_admin.extensions import register_extensions
from pear_admin.orms import UserORM
from pear_admin.views import register_views


def create_app(config_name="dev"):
    import os
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(BASE_DIR, 'templates')
    static_dir = os.path.join(BASE_DIR, 'static')

    app = Flask("pear-admin-flask", template_folder=template_dir, static_folder=static_dir)

    app.config.from_object(config[config_name])

    register_extensions(app)
    register_apis(app)

    register_views(app)

    @app.errorhandler(403)
    def handle_404(e):
        return render_template("error/403.html")

    @app.errorhandler(404)
    def handle_403(e):
        return render_template("error/404.html")

    @app.errorhandler(500)
    def handle_500(e):
        return render_template("error/500.html")

    return app


__all__ = ["UserORM"]
