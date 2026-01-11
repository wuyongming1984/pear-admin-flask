import os

from flask import Blueprint, render_template, send_from_directory
from flask_jwt_extended import jwt_required

from configs import config

project_bp = Blueprint("project", __name__)


# 数据库菜单配置的路由
@project_bp.route("/project/info/project_info.html")
def project_info():
    return render_template("project/info/project_info.html")


# 文件下载路由
@project_bp.route("/uploads/<filename>")
def download_file(filename):
    upload_folder = config["dev"].UPLOAD_FOLDER
    return send_from_directory(upload_folder, filename)





