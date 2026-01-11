import os
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename

from pear_admin.extensions import db
from pear_admin.orms import AttachmentORM

upload_api = Blueprint("upload", __name__, url_prefix="/upload")

ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx',
    'ppt', 'pptx', 'zip', 'rar', 'dwg', 'dgn', 'dwf', 'dxf'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_api.post("/")
@jwt_required()
def upload_file():
    if 'file' not in request.files:
        return {"code": -1, "msg": "没有文件被上传"}
    
    file = request.files['file']
    if file.filename == '':
        return {"code": -1, "msg": "文件名为空"}
    
    if not allowed_file(file.filename):
        return {"code": -1, "msg": "不支持的文件类型"}
    
    # 获取项目ID和附件编号（可选，用于关联项目）
    project_id = request.form.get("project_id", type=int)
    attachment_code = request.form.get("attachment_code", type=str)
    
    try:
        # 生成安全的文件名
        filename = secure_filename(file.filename)
        # 添加时间戳避免文件名冲突
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{timestamp}{ext}"
        
        # 创建上传目录
        upload_folder = Path(current_app.config.get('UPLOAD_FOLDER', 'uploads'))
        upload_folder.mkdir(parents=True, exist_ok=True)
        
        # 保存文件
        file_path = upload_folder / filename
        file.save(str(file_path))
        
        # 文件相对路径（用于下载）
        file_url = f"/uploads/{filename}"
        
        # 如果提供了项目ID和附件编号，保存到数据库
        attachment_id = None
        if project_id and attachment_code:
            attachment = AttachmentORM(
                project_id=project_id,
                attachment_code=attachment_code,
                filename=filename,
                original_filename=file.filename,
                file_path=file_url,
                file_size=file_path.stat().st_size
            )
            attachment.save()
            attachment_id = attachment.id
        
        # 返回文件信息
        return {
            "code": 0,
            "msg": "上传成功",
            "data": {
                "id": attachment_id,
                "filename": filename,
                "original_filename": file.filename,
                "url": file_url,
                "size": file_path.stat().st_size
            }
        }
    except Exception as e:
        return {"code": -1, "msg": f"上传失败: {str(e)}"}

