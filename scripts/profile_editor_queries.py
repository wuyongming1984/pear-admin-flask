"""Read-only editor query counts on the deployment's database.

Run inside the web container:
  python scripts/profile_editor_queries.py --config prod
Optional: --order-id 123 --payment-id 456 --repeat 2
System list audit: --scope system (first 20 rows of each paginated list)
Order/payment deployment check: --scope documents (desktop and mobile lists)

No app factory, scheduler, migrations, write endpoints, record contents or
credentials. Timings exclude browser/network, nginx and Gunicorn queuing.
The temporary JWT secret is private to this diagnostic app; tokens never leave
the process and cannot be used to authenticate against the running server.
"""
import argparse
import json
import math
import secrets
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def create_diagnostic_app(config_name):
    from flask import Flask
    from configs import config
    from pear_admin.apis import register_apis
    from pear_admin.extensions import db, jwt, oss

    app = Flask('editor-query-profile', instance_path=str(ROOT / 'instance'))
    app.config.from_object(config[config_name])
    app.config.update(TESTING=True, JWT_SECRET_KEY=secrets.token_urlsafe(48),
                      JWT_VERIFY_SUB=False, SQLALCHEMY_ECHO=False)
    db.init_app(app)
    jwt.init_app(app)
    oss.init_app(app)
    register_apis(app)
    return app


def profile_request(app, path, headers):
    from sqlalchemy import event
    from pear_admin.extensions import db

    db.session.remove()
    durations = []
    def before(conn, cursor, statement, parameters, context, executemany):
        if not statement.lstrip().upper().startswith('SELECT'):
            raise RuntimeError('Non-SELECT statement blocked by read-only profiler')
        context.editor_profile_started = perf_counter()
    def after(conn, cursor, statement, parameters, context, executemany):
        durations.append((perf_counter() - context.editor_profile_started) * 1000)
    engine = db.engine
    event.listen(engine, 'before_cursor_execute', before)
    event.listen(engine, 'after_cursor_execute', after)
    start = perf_counter()
    try:
        response = app.test_client().get('/api/v1' + path, headers=headers)
        elapsed = (perf_counter() - start) * 1000
        payload = response.get_json(silent=True) or {}
        rows = payload.get('data')
        result = dict(path=path, status=response.status_code, code=payload.get('code'),
                      sql_count=len(durations), sql_ms=round(sum(durations), 2),
                      elapsed_ms=round(elapsed, 2), response_bytes=len(response.data))
        if isinstance(rows, list):
            result.update(batch_rows=len(rows), total_rows=payload.get('count'))
            if rows and payload.get('count') is not None:
                result['pages_for_allRows'] = math.ceil(payload['count'] / len(rows))
        return result
    finally:
        event.remove(engine, 'before_cursor_execute', before)
        event.remove(engine, 'after_cursor_execute', after)
        db.session.remove()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', choices=['dev', 'prod'], default='prod')
    parser.add_argument('--scope', choices=['editor', 'system', 'documents'], default='editor')
    parser.add_argument('--order-id', type=int)
    parser.add_argument('--payment-id', type=int)
    parser.add_argument('--repeat', type=int, choices=range(1, 4), default=1)
    args = parser.parse_args()
    from flask_jwt_extended import create_access_token
    from pear_admin.extensions import db
    from pear_admin.orms import OrderORM, PayORM, UserORM

    app = create_diagnostic_app(args.config)
    with app.app_context():
        user = db.session.scalar(db.select(UserORM).order_by(UserORM.id).limit(1))
        if user is None:
            raise RuntimeError('No existing user is available for in-process authentication')
        headers = {'Authorization': 'Bearer ' + create_access_token(identity=user)}
        order_id = args.order_id or db.session.scalar(db.select(OrderORM.id).order_by(OrderORM.id.desc()).limit(1))
        pay_id = args.payment_id or db.session.scalar(db.select(PayORM.id).order_by(PayORM.id.desc()).limit(1))
        print(json.dumps({'database': db.engine.url.get_backend_name(),
                          'scope': 'in-process GET requests; no records or credentials included'}, ensure_ascii=False))
        paths = ['/project/?mode=slim&page=1&limit=500',
                 '/order/?mode=options&page=1&limit=500',
                 '/supplier/?mode=slim&page=1&limit=500', '/payer/?page=1&limit=500',
                 '/dictionary/detail/list?dic_id=35&page=1&limit=500',
                 '/dictionary/detail/list?dic_id=28&page=1&limit=500']
        if order_id:
            paths.append(f'/order/{order_id}')
        if pay_id:
            paths.append(f'/pay/{pay_id}')
        if args.scope == 'system':
            paths = ['/project/?page=1&limit=20', '/order/?page=1&limit=20',
                     '/pay/?page=1&limit=20',
                     '/workspace/orders?page=1&limit=20', '/workspace/payments?page=1&limit=20',
                     '/dashboard/overview', '/material/options',
                     '/material/planning?page=1&limit=20',
                     '/material/inbound?page=1&limit=20&status=pending',
                     '/material/inventory?page=1&limit=20',
                     '/material/outbound?page=1&limit=20',
                     '/material/invoice?page=1&limit=20',
                     '/material/dashboard/stats', '/nursery/dashboard/stats']
            # /nursery/orders returns full history; deliberately exclude it from
            # the production default to avoid an unbounded diagnostic response.
        elif args.scope == 'documents':
            paths = ['/workspace/orders?page=1&limit=20', '/workspace/payments?page=1&limit=20',
                     '/order/?page=1&limit=3', '/pay/?page=1&limit=3']
        for run in range(args.repeat):
            for path in paths:
                result = profile_request(app, path, headers)
                print(json.dumps({'run': run + 1, **result}, ensure_ascii=False), flush=True)
                if result['status'] != 200 or result['code'] != 0:
                    raise RuntimeError(f'API check failed: {path}')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Driver exception messages may contain connection settings or SQL data.
        print(json.dumps({'error_type': type(error).__name__, 'message': 'Profiling failed; check configuration and database access on the server.'}), file=sys.stderr)
        raise SystemExit(1)
