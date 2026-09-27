"""Serve a disposable local SQLite copy; never starts migrations or schedulers."""
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flask import Flask, request, render_template_string
from pear_admin.extensions import db, jwt, oss
from pear_admin.apis import register_apis
from pear_admin.views import register_views

folder = Path(tempfile.mkdtemp(prefix='pear-pc-audit-'))
source = sqlite3.connect('file:' + (ROOT / 'instance/pear_admin.db').as_posix() + '?mode=ro', uri=True)
with sqlite3.connect(folder / 'audit.db') as dest:
    source.backup(dest)
source.close()
app = Flask('pc-audit', static_folder=str(ROOT / 'static'), template_folder=str(ROOT / 'templates'))
app.config.update(SECRET_KEY='isolated-local-pc-audit', SQLALCHEMY_DATABASE_URI='sqlite:///' + (folder / 'audit.db').as_posix(), UPLOAD_FOLDER=str(folder / 'uploads'), DEBUG=False)
db.init_app(app)
jwt.init_app(app)
oss.init_app(app)
register_apis(app)
register_views(app)
@app.get('/__audit')
def audit_shell():
    pages = sorted({str(rule) for rule in app.url_map.iter_rules()
                    if 'GET' in rule.methods and '<' not in str(rule)
                    and not str(rule).startswith(('/api/', '/static', '/__audit', '/m/', '/favicon'))})
    extra = ['/project/info/project_info.html', '/supplier/info/supplier_info.html', '/payer/info/payer_info.html',
             '/order_pay/base/order_base.html', '/order_pay/base/pay_base.html',
             '/order_pay/info/order_info.html', '/order_pay/info/pay_info.html',
             '/system/rights/index.html', '/system/dictionary/index.html']
    pages = sorted(set(pages + extra))
    target = request.args.get('page')
    if not target:
        return render_template_string('<h1>本地页面验收目录</h1>{% for p in pages %}<p><a href="{{ url_for("audit_shell",page=p) }}">{{p}}</a></p>{% endfor %}', pages=pages)
    if target not in pages:
        return 'Unknown audit page', 404
    return render_template_string('''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
    <link rel="stylesheet" href="/static/component/pear/css/pear.css">
    <link rel="stylesheet" href="/static/admin/css/variables.css">
    <link rel="stylesheet" href="/static/admin/css/reset.css">
    <link rel="stylesheet" href="/static/admin/css/desktop-refined.css">
    <script src="/static/component/layui/layui.js"></script><script src="/static/component/pear/pear.js"></script>
    </head><body class="sf-audit"><p style="padding:10px;background:#e8f4f0"><a href="/__audit">验收目录</a> · {{target}}</p>
    <span id="audit-status" role="status">正在准备页面</span><main id="audit-content"></main><script>layui.use(['jquery'],function(){var $=layui.jquery;
    $.ajaxSetup({headers:{Authorization:'Bearer '+localStorage.getItem('access_token')}});
    $('#audit-content').load({{target|tojson}},function(){ $('#audit-status').text('页面加载完成'); });});</script></body></html>''', target=target)
print('AUDIT_COPY=' + str(folder), flush=True)
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5052, use_reloader=False)
