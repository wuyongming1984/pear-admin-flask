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
    
    
    # 获取存储路径 (e.g. "order_attachments")
    custom_path = request.form.get("path", "").strip()
    
    # Check allowed extensions
    # Relax restrictions for order and pay attachments as requested
    if custom_path not in ['order_attachments', 'pay_attachments']:
        if not allowed_file(file.filename):
            return {"code": -1, "msg": "不支持的文件类型"}
    
    # 获取项目ID和附件编号（可选，用于关联项目）
    project_id = request.form.get("project_id", type=int)
    attachment_code = request.form.get("attachment_code", type=str)
    
    try:
        # 获取存储路径 (e.g. "order_attachments")
        custom_path = request.form.get("path", "").strip()
        
        # Determine Naming Rule based on Path
        # Only 'order_attachments' and 'pay_attachments' use the new rule
        if custom_path in ['order_attachments', 'pay_attachments']:
             # Rule: Date_UniqueSequence_OriginalFilename
             # 日期_不重复的流水号_原文件名
             import uuid
             import re
             
             date_str = datetime.now().strftime("%Y%m%d")
             unique_seq = str(uuid.uuid4().hex)[:8]
             
             def clean_filename(name):
                 # Keep Chinese, letters, numbers, dots, underscores, dashes
                 cleaned = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9._-]', '', name)
                 return cleaned.strip()

             original_name = clean_filename(file.filename)
             if not original_name.strip():
                 original_name = "file"
                 
             filename = f"{date_str}_{unique_seq}_{original_name}"
        else:
             # Default Rule: OriginalName_Timestamp
             # Keep secure_filename for other paths as fallback
             safe_name = secure_filename(file.filename)
             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
             name, ext = os.path.splitext(safe_name)
             filename = f"{name}_{timestamp}{ext}"
        
        # 获取存储路径 (e.g. "order_attachments")
        custom_path = request.form.get("path", "").strip()
        if custom_path:
             # Ensure no leading/trailing slashes for consistency
             custom_path = custom_path.strip('/')
             object_key = f"{custom_path}/{filename}"
        else:
             object_key = f"uploads/{filename}"

        from pear_admin.extensions import oss
        
        # 优先尝试 OSS 上传
        if oss.bucket:
             url = oss.upload_file(file, filename=object_key)
             file_url = url
             file_size = 0 # OSS 上传暂时不获取大小，或者需要先 seek(0,2) tell()
             # 为了获取大小，可以:
             file.seek(0, os.SEEK_END)
             file_size = file.tell()
             file.seek(0)
        else:
            # 本地存储回退
            # 创建上传目录
            upload_folder = Path(current_app.config.get('UPLOAD_FOLDER', 'uploads'))
            if custom_path:
                upload_folder = upload_folder / custom_path
            
            upload_folder.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            file_path = upload_folder / filename
            file.save(str(file_path))
            file_size = file_path.stat().st_size
            
            # 文件相对路径（用于下载）
            file_url = f"/uploads/{custom_path + '/' if custom_path else ''}{filename}"
            # 注意: 这里假设静态文件服务能映射到 uploads 目录。
            # 如果 custom_path 变更，可能需要调整 static 路由，或者统一 put 到 uploads/ 下
            # 为了简单起见，本地存储时尽量保持扁平或确保 static 能访问
            if custom_path:
                 # Local path hack: store everything in uploads root if we can't ensure subfolder serving
                 pass 

        # 如果提供了项目ID和附件编号，保存到数据库
        attachment_id = None
        if project_id and attachment_code:
            attachment = AttachmentORM(
                project_id=project_id,
                attachment_code=attachment_code,
                filename=filename,
                original_filename=file.filename,
                file_path=file_url,
                file_size=file_size
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
                "size": file_size,
                "code": attachment_code # 回传附件编号方便前端使用
            }
        }
    except Exception as e:
        return {"code": -1, "msg": f"上传失败: {str(e)}"}

