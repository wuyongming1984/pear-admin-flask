"""Create receipt tables and place the menu immediately below the invoice library.

Local: python scripts/migrate_payment_receipts.py --sqlite instance/pear_admin.db
Server: python scripts/migrate_payment_receipts.py --config prod
No Flask application, scheduler, OCR or storage clients are started.
"""
import argparse
from contextlib import closing
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import sys
from sqlalchemy import create_engine, inspect, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MENU_URL = '/view/payment-receipts'
RECEIPT_TABLES = {'payment_receipt', 'pay_receipt_relation'}


def _menu_state(connection):
    snapshot = {table: [dict(row) for row in connection.execute(text(f'SELECT * FROM {table} ORDER BY id')).mappings()]
                for table in ('ums_rights', 'ums_role_rights')}
    anchor = next((row for row in snapshot['ums_rights'] if row['url'] == '/view/material/invoice'), None)
    if not anchor:
        raise ValueError('Invoice menu not found; no menu or schema was changed')
    menu = next((row for row in snapshot['ums_rights'] if row['url'] == MENU_URL), None)
    desired = {'name': '付款回单库', 'code': 'payment:receipts', 'type': 'path',
               'status': 1, 'sort': (anchor['sort'] or 0) + 1,
               'open_type': '_iframe', 'pid': anchor['pid']}
    # Legacy imports use pid=0 with FK checks disabled. NULL is the same root
    # in nested(), and remains valid when the self-referencing FK is enforced.
    if anchor['pid'] == 0 and not any(row['id'] == 0 for row in snapshot['ums_rights']):
        if any('pid' in key['constrained_columns'] and key['referred_table'] == 'ums_rights'
               for key in inspect(connection).get_foreign_keys('ums_rights')):
            desired['pid'] = None
    roles = {row['role_id'] for row in snapshot['ums_role_rights'] if row['rights_id'] == anchor['id']}
    existing_roles = {row['role_id'] for row in snapshot['ums_role_rights'] if menu and row['rights_id'] == menu['id']}
    collision = any(row['id'] != (menu or {}).get('id') and
                    (row['pid'] or 0) == (anchor['pid'] or 0) and
                    ((row['sort'] or 0) == desired['sort'] or
                     ((row['sort'] or 0) == (anchor['sort'] or 0) and row['id'] > anchor['id']))
                    for row in snapshot['ums_rights'])
    return snapshot, anchor, menu, desired, roles - existing_roles, existing_roles, collision


def check(engine, username=None):
    """Inspect menu placement, schema and role grants without changing the database."""
    tables = set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        snapshot, anchor, menu, desired, missing_roles, roles, collision = _menu_state(connection)
        errors = []
        if not menu:
            errors.append('Receipt menu missing')
        else:
            errors.extend(f'Menu field needs repair: {key}' for key, value in desired.items() if menu[key] != value)
        if collision:
            errors.append('Receipt position is occupied by another sibling')
        if missing_roles:
            errors.append('Invoice roles are missing receipt grants')
        missing_tables = sorted(RECEIPT_TABLES - tables)
        if missing_tables:
            errors.append('Receipt tables missing')
        result = {'ready': not errors, 'menu_id': menu['id'] if menu else None,
                  'menu': menu, 'invoice_id': anchor['id'], 'errors': errors,
                  'missing_tables': missing_tables, 'missing_role_ids': sorted(missing_roles),
                  'receipt_role_ids': sorted(roles)}
        if username:
            if not {'ums_user', 'ums_user_role'} <= tables:
                raise ValueError('User role tables not found; cannot check account visibility')
            user_id = connection.execute(text('SELECT id FROM ums_user WHERE username=:username ORDER BY id LIMIT 1'), {'username': username}).scalar()
            granted = set(connection.execute(text('''SELECT DISTINCT rr.rights_id FROM ums_role_rights rr
                JOIN ums_user_role ur ON ur.role_id=rr.role_id WHERE ur.user_id=:id'''), {'id': user_id}).scalars())
            menus = {row['id']: row for row in snapshot['ums_rights']}
            visible = bool(user_id and menu)
            current = menu
            seen = set()
            while visible and current:
                if current['id'] in seen or current['id'] not in granted or current['type'] not in ('path', 'menu'):
                    visible = False
                    break
                seen.add(current['id'])
                if not current['pid']:
                    break
                current = menus.get(current['pid'])
                if not current:
                    visible = False
            result.update(username=username, user_found=user_id is not None, user_receipt_visible=visible)
    return result


def upgrade(engine, backup_directory):
    from pear_admin.orms import PaymentReceiptORM
    from pear_admin.orms.payment_receipt import pay_receipt_relation

    with engine.connect() as connection:
        snapshot, anchor, menu, desired, missing_roles, _, collision = _menu_state(connection)
    missing = RECEIPT_TABLES - set(inspect(engine).get_table_names())
    menu_changed = not menu or any(menu[key] != value for key, value in desired.items())
    if not missing and not menu_changed and not missing_roles and not collision:
        return {'menu_id': menu['id'], 'backup': None}

    directory = Path(backup_directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = directory / f'payment-receipts-menu-{stamp}.json'
    with backup.open('x', encoding='utf-8') as output:
        json.dump(snapshot, output, ensure_ascii=False, indent=2, default=str)
    if engine.dialect.name == 'sqlite':
        with engine.connect() as connection, closing(sqlite3.connect(directory / f'payment-receipts-{stamp}.db')) as destination:
            connection.connection.driver_connection.backup(destination)
    # Create only these two tables; existing business schema is untouched.
    PaymentReceiptORM.metadata.create_all(engine, tables=[PaymentReceiptORM.__table__, pay_receipt_relation])
    with engine.begin() as connection:
        # Re-read inside the transaction; preserve existing IDs and unrelated grants.
        current_snapshot, anchor, menu, desired, missing_roles, _, collision = _menu_state(connection)
        menu_id = menu['id'] if menu else None
        moved = not menu or menu['pid'] != desired['pid'] or menu['sort'] != desired['sort']
        if moved or collision:
            tied = any(row['id'] != menu_id and row['id'] > anchor['id'] and
                       (row['pid'] or 0) == (anchor['pid'] or 0) and
                       (row['sort'] or 0) == (anchor['sort'] or 0) for row in current_snapshot['ums_rights'])
            connection.execute(text('''UPDATE ums_rights SET sort=CASE
                    WHEN COALESCE(sort,0)=:anchor_sort THEN :sort+1 ELSE sort+:shift END
                WHERE COALESCE(pid,0)=:parent AND (:id IS NULL OR id<>:id)
                  AND (sort>=:sort OR (COALESCE(sort,0)=:anchor_sort AND id>:anchor_id))'''),
                {'parent': desired['pid'] or 0, 'sort': desired['sort'], 'id': menu_id,
                 'anchor_sort': anchor['sort'] or 0, 'anchor_id': anchor['id'], 'shift': 2 if tied else 1})
        if not menu:
            result = connection.execute(text('''INSERT INTO ums_rights
                (name,code,type,url,icon_sign,status,sort,open_type,pid)
                VALUES ('付款回单库','payment:receipts','path',:url,
                        'layui-icon layui-icon-file',1,:sort,'_iframe',:pid)'''),
                {'url': MENU_URL, 'sort': desired['sort'], 'pid': desired['pid']})
            menu_id = result.lastrowid
        else:
            connection.execute(text('''UPDATE ums_rights SET name=:name,code=:code,type=:type,
                status=:status,sort=:sort,open_type=:open_type,pid=:pid WHERE id=:id'''),
                dict(desired, id=menu_id))
        for role in sorted(missing_roles):
            connection.execute(text('INSERT INTO ums_role_rights (rights_id,role_id) VALUES (:id,:role)'), {'id': menu_id, 'role': role})
    report = check(engine)
    if not report['ready']:
        raise ValueError('Receipt migration verification failed: ' + '; '.join(report['errors']))
    return {'menu_id': menu_id, 'backup': backup}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--sqlite', type=Path)
    target.add_argument('--config', choices=['prod'])
    parser.add_argument('--backup-dir', type=Path, default=ROOT / 'instance' / 'receipt-migration-backups')
    parser.add_argument('--check', action='store_true', help='Read-only schema/menu/grant verification')
    parser.add_argument('--user', help='Verify sidebar visibility for this login name')
    args = parser.parse_args()
    if args.sqlite:
        uri = 'sqlite:///' + args.sqlite.resolve(strict=True).as_posix()
    else:
        from configs import config
        uri = config[args.config].SQLALCHEMY_DATABASE_URI
    engine = create_engine(uri)
    try:
        if not args.check:
            result = upgrade(engine, args.backup_dir)
            print(f"Receipt menu backup: {result['backup'] or 'unchanged'}")
        report = check(engine, args.user)
        print(f'Database: dialect={engine.dialect.name}, host={engine.url.host or "local"}, database={engine.url.database}')
        menu = report['menu'] or {}
        print(f"Receipt menu: id={report['menu_id']}, invoice={report['invoice_id']}, pid={menu.get('pid')}, sort={menu.get('sort')}, status={menu.get('status')}, type={menu.get('type')}, url={menu.get('url')}")
        print(f"Receipt role grants: {report['receipt_role_ids']}; missing invoice roles: {report['missing_role_ids']}")
        print(f"Receipt tables: {'OK' if not report['missing_tables'] else ','.join(report['missing_tables'])}")
        if args.user:
            print(f"User {args.user}: found={report['user_found']}, receipt_visible={report['user_receipt_visible']}")
        for error in report['errors']:
            print(error, file=sys.stderr)
        if not report['ready'] or (args.user and not report['user_receipt_visible']):
            raise SystemExit(1)
        print('Receipt library ready')
    finally:
        engine.dispose()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        detail = str(error) if isinstance(error, ValueError) else 'check database access and menu hierarchy'
        print(f'Receipt migration failed ({type(error).__name__}): {detail}', file=sys.stderr)
        raise SystemExit(1)
