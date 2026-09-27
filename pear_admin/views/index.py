from pathlib import Path

from flask import Blueprint, current_app, render_template, send_from_directory, redirect

index_bp = Blueprint("index", __name__)


@index_bp.route("/")
def index():
    if current_app.config.get('DESKTOP_DEFAULT', False):
        return redirect('/pc/')
    return render_template("view/index.html")


@index_bp.get('/legacy/')
def legacy():
    return render_template('view/index.html')


@index_bp.get('/pc/')
def desktop():
    folder = Path(current_app.static_folder) / 'desktop'
    if not (folder / 'index.html').is_file():
        return '新版电脑端尚未构建，请先完成 frontend-desktop 构建。', 503
    response = send_from_directory(folder, 'index.html', max_age=0)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


@index_bp.route("/view/login.html")
def login():
    return render_template("view/login.html")


@index_bp.route("/view/register.html")
def register():
    return render_template("view/register.html")


@index_bp.route("/view/console/index.html")
def console1():
    return render_template("view/console/index.html")


@index_bp.route("/view/analysis/index.html")
def analysis():
    return render_template("view/analysis/index.html")


@index_bp.route("/view/system/person.html")
def person():
    return render_template("view/system/person.html")


@index_bp.route("/favicon.ico")
def fav_icon():
    return send_from_directory(directory="static", path="favicon.ico")


@index_bp.get("/m/")
def mobile():
    response = send_from_directory(Path(current_app.static_folder) / "mobile", "index.html", max_age=0)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@index_bp.get("/uploads/<path:filename>")
def nested_upload(filename):
    # The existing flat-file route remains more specific. This adds nested upload paths.
    folder = Path(current_app.config.get("UPLOAD_FOLDER", "uploads")).resolve()
    return send_from_directory(folder, filename)
