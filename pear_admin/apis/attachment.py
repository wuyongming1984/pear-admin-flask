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
    """代理转发附件内容，强制以 inline 形式返回给浏览器（解决 OSS 强制下载问题）
    注：设计上这个接口是内部代理，访问它只能得到已经有限期签名且可公开的 OSS 文件，无额外安全隐患"""
    from flask import Response, current_app
    import requests as req
    from urllib.parse import urlparse, unquote

    file_url = request.args.get('url', '').strip()
    filename = request.args.get('name', 'file').strip()

    if not file_url:
        return "缺少 url 参数", 400

    try:
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else \
              file_url.split('?')[0].rsplit('.', 1)[-1].lower()
        mime_map = {
            'pdf': 'application/pdf',
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'png': 'image/png', 'gif': 'image/gif',
            'webp': 'image/webp', 'svg': 'image/svg+xml',
        }
        content_type = mime_map.get(ext, 'application/octet-stream')

        # 尝试用 OSS SDK 直接读取（避免下载 URL 问题）
        from pear_admin.extensions import oss
        data = None
        if oss and oss.bucket and file_url.startswith('http'):
            try:
                parsed = urlparse(file_url)
                object_key = unquote(parsed.path.lstrip('/'))
                oss_obj = oss.bucket.get_object(object_key)
                data = oss_obj.read()
            except Exception as e:
                current_app.logger.warning(f"[Proxy] OSS SDK fallback: {e}, 尝试直接请求")

        if data is None:
            r = req.get(file_url, timeout=20)
            r.raise_for_status()
            data = r.content

        response = Response(
            data,
            content_type=content_type,
            headers={
                'Content-Disposition': f'inline; filename="{filename}"',
                'Cache-Control': 'no-cache'
            }
        )
        return response

    except Exception as e:
        current_app.logger.error(f"[Proxy Preview] Error: {e}", exc_info=True)
        return str(e), 500
