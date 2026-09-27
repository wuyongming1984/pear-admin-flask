"""PDF previews independent of browser PDF plugins and OSS download headers."""
import base64
from pathlib import Path
from urllib.parse import unquote, urlparse
from flask import current_app
from werkzeug.exceptions import BadRequest, NotFound, RequestEntityTooLarge, UnprocessableEntity, ServiceUnavailable
from pear_admin.extensions import oss

MAX_FILE_BYTES = 20 * 1024 * 1024


def read_original(file_path):
    parsed = urlparse(file_path)
    if parsed.scheme or parsed.netloc:
        bucket = oss.bucket
        endpoint = bucket.endpoint if bucket else current_app.config.get('ALIYUN_OSS_ENDPOINT', '')
        bucket_name = bucket.bucket_name if bucket else current_app.config.get('ALIYUN_OSS_BUCKET_NAME', '')
        endpoint_host = urlparse(endpoint if '://' in endpoint else 'https://' + endpoint).hostname
        expected_host = f'{bucket_name}.{endpoint_host}' if bucket_name and endpoint_host else None
        if parsed.scheme not in ('http', 'https') or not expected_host or parsed.hostname != expected_host or parsed.port not in (None, 80, 443):
            raise BadRequest('原文件地址不属于当前文件存储')
        if not bucket:
            raise ServiceUnavailable('文件存储尚未配置，暂时无法预览')
        # SDK authentication also works for private objects, without cross-origin browser requests.
        stream = bucket.get_object(unquote(parsed.path.lstrip('/')))
    else:
        path = unquote(file_path).replace('\\', '/').lstrip('/')
        if path.startswith('static/uploads/'):
            root = Path(current_app.static_folder) / 'uploads'
            relative = path[len('static/uploads/'):]
        elif path.startswith('uploads/'):
            root = Path(current_app.config.get('UPLOAD_FOLDER') or Path(current_app.root_path).parent / 'uploads')
            relative = path[len('uploads/'):]
        else:
            raise BadRequest('不支持的原文件路径')
        root = root.resolve()
        target = (root / relative).resolve()
        if not target.is_relative_to(root):
            raise BadRequest('无效的原文件路径')
        if not target.is_file():
            raise NotFound('原文件不存在')
        if target.stat().st_size > MAX_FILE_BYTES:
            raise RequestEntityTooLarge('文件超过 20 MB，请下载原文件查看')
        stream = target.open('rb')
    try:
        data = stream.read(MAX_FILE_BYTES + 1)
    finally:
        close = getattr(stream, 'close', None)
        if close:
            close()
    if len(data) > MAX_FILE_BYTES:
        raise RequestEntityTooLarge('文件超过 20 MB，请下载原文件查看')
    return data


def render_pdf_page(file_path, page_number):
    import pymupdf
    data = read_original(file_path)
    try:
        doc = pymupdf.open(stream=data, filetype='pdf')
    except (pymupdf.FileDataError, RuntimeError, ValueError):
        raise UnprocessableEntity('原文件不是有效的 PDF，或文件已损坏')
    with doc:
        if doc.needs_pass:
            raise UnprocessableEntity('此 PDF 已加密，请下载原文件查看')
        if not 1 <= page_number <= doc.page_count:
            raise BadRequest('预览页码超出范围')
        page = doc[page_number - 1]
        longest = max(page.rect.width, page.rect.height)
        if longest <= 0:
            raise UnprocessableEntity('PDF 页面尺寸无效')
        scale = min(2, 1800 / longest)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csRGB, alpha=False)
        return {'page': page_number, 'page_count': doc.page_count,
                'image': 'data:image/png;base64,' + base64.b64encode(pix.tobytes('png')).decode('ascii')}
