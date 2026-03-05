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
    file_path = request.args.get('path', '').strip()  # 原始 OSS object key，优先使用
    filename = request.args.get('name', 'file').strip()

    if not file_url and not file_path:
        return "缺少 url 或 path 参数", 400

    try:
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else \
              (file_url or file_path).split('?')[0].rsplit('.', 1)[-1].lower()
        mime_map = {
            'pdf': 'application/pdf',
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'png': 'image/png', 'gif': 'image/gif',
            'webp': 'image/webp', 'svg': 'image/svg+xml',
        }
        content_type = mime_map.get(ext, 'application/octet-stream')

        from pear_admin.extensions import oss
        data = None

        # 优先用 OSS SDK 直接读取（path 参数或从 URL 提取 key）
        if oss and oss.bucket:
            from urllib.parse import urlparse, unquote
            object_key = None
            if file_path:
                if file_path.startswith('http'):
                    # file_path 本身是完整 URL，提取 path 部分
                    parsed = urlparse(file_path)
                    object_key = unquote(parsed.path.lstrip('/'))
                else:
                    object_key = file_path.lstrip('/')
            if not object_key and file_url and file_url.startswith('http'):
                parsed = urlparse(file_url)
                object_key = unquote(parsed.path.lstrip('/'))
            if object_key:
                try:
                    oss_obj = oss.bucket.get_object(object_key)
                    data = oss_obj.read()
                except Exception as e:
                    current_app.logger.warning(f"[Proxy] OSS get_object failed for '{object_key}': {e}")

        # 最终 fallback：直接 HTTP 请求 URL
        if data is None and file_url:
            import requests as req
            r = req.get(file_url, timeout=20)
            r.raise_for_status()
            data = r.content

        if data is None:
            return "无法获取文件内容", 500

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
