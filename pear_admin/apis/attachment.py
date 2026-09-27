from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from pear_admin.extensions import db
from pear_admin.orms import AttachmentORM

attachment_api = Blueprint("attachment", __name__, url_prefix="/attachment")


@attachment_api.delete("/<int:aid>")
@jwt_required()
def delete_attachment(aid):
    attachment = AttachmentORM.query.get(aid)
    if not attachment:
        return {"code": -1, "msg": "附件不存在"}
    
    attachment.delete()
    return {"code": 0, "msg": "删除附件成功"}


@attachment_api.get("/project/<int:pid>")
@jwt_required()
def get_project_attachments(pid):
    attachments = AttachmentORM.query.filter_by(project_id=pid).all()
    return {
        "code": 0,
        "msg": "获取附件列表成功",
        "data": [att.json() for att in attachments]
    }


@attachment_api.get("/proxy-preview")
def proxy_preview():
    """代理转发附件内容，强制以 inline 形式返回给浏览器（解决 OSS 强制下载问题）"""
    try:
        from flask import Response, current_app
        from urllib.parse import urlparse, unquote

        file_url = request.args.get('url', '').strip()
        file_path = request.args.get('path', '').strip()
        filename = request.args.get('name', 'file').strip()

        if not file_url and not file_path:
            return "缺少 url 或 path 参数", 400

        ext = ''
        if '.' in filename:
            ext = filename.rsplit('.', 1)[-1].lower()
        elif file_path:
            ext = file_path.split('?')[0].rsplit('.', 1)[-1].lower() if '.' in file_path else ''
        elif file_url:
            ext = file_url.split('?')[0].rsplit('.', 1)[-1].lower() if '.' in file_url else ''

        mime_map = {
            'pdf': 'application/pdf',
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'png': 'image/png', 'gif': 'image/gif',
            'webp': 'image/webp', 'svg': 'image/svg+xml',
        }
        content_type = mime_map.get(ext, 'application/octet-stream')

        data = None

        # 优先用 OSS SDK 直接读取
        try:
            from pear_admin.extensions import oss
            if oss and oss.bucket:
                object_key = None
                if file_path:
                    if file_path.startswith('http'):
                        parsed = urlparse(file_path)
                        object_key = unquote(parsed.path.lstrip('/'))
                    else:
                        object_key = file_path.lstrip('/')
                if not object_key and file_url and file_url.startswith('http'):
                    parsed = urlparse(file_url)
                    object_key = unquote(parsed.path.lstrip('/'))
                if object_key:
                    oss_obj = oss.bucket.get_object(object_key)
                    data = oss_obj.read()
        except Exception as oss_err:
            try:
                from flask import current_app
                current_app.logger.warning(f"[Proxy] OSS read failed: {oss_err}")
            except:
                pass

        # fallback：HTTP 请求原始 URL
        if data is None:
            target_url = file_url or file_path
            if not target_url:
                return "无法获取文件（无 URL）", 500
            try:
                import requests as req_lib
                r = req_lib.get(target_url, timeout=20)
                r.raise_for_status()
                data = r.content
            except Exception as http_err:
                return f"HTTP 请求失败: {http_err}", 500

        if data is None:
            return "无法获取文件内容", 500

        from urllib.parse import quote
        # RFC 5987 编码文件名，解决中文文件名导致部分 WSGI 服务器报 500 错误的问题
        quoted_filename = quote(filename)
        headers = {
            'Content-Disposition': f'inline; filename="{quoted_filename}"; filename*=UTF-8\'\'{quoted_filename}',
            'Cache-Control': 'no-cache'
        }
        
        response = Response(
            data,
            content_type=content_type,
            headers=headers
        )
        return response

    except Exception as e:
        try:
            from flask import current_app
            current_app.logger.error(f"[Proxy Preview] Unhandled error: {e}", exc_info=True)
        except:
            pass
        return f"代理异常: {str(e)}", 500
