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


def upgrade(engine, backup_directory):
    from pear_admin.orms import PaymentReceiptORM
    from pear_admin.orms.payment_receipt import pay_receipt_relation

    with engine.connect() as connection:
        menu_id = connection.execute(text('SELECT id FROM ums_rights WHERE url=:url ORDER BY id LIMIT 1'), {'url': MENU_URL}).scalar()
        anchor = connection.execute(text("SELECT * FROM ums_rights WHERE url='/view/material/invoice' ORDER BY id LIMIT 1")).mappings().first()
        if not anchor and not menu_id:
            raise ValueError('Invoice menu not found; no menu or schema was changed')
        snapshot = {table: [dict(row) for row in connection.execute(text(f'SELECT * FROM {table} ORDER BY id')).mappings()]
                    for table in ('ums_rights', 'ums_role_rights')}
    missing = {'payment_receipt', 'pay_receipt_relation'} - set(inspect(engine).get_table_names())
    if not missing and menu_id:
        return {'menu_id': menu_id, 'backup': None}

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
    if not menu_id:
        with engine.begin() as connection:
            parent = anchor['pid'] or 0
            position = (anchor['sort'] or 0) + 1
            connection.execute(text('UPDATE ums_rights SET sort=sort+1 WHERE pid=:pid AND sort>=:sort'), {'pid': parent, 'sort': position})
            result = connection.execute(text('''INSERT INTO ums_rights
                (name,code,type,url,icon_sign,status,sort,open_type,pid)
                VALUES ('付款回单库','payment:receipts','path',:url,
                        'layui-icon layui-icon-file',1,:sort,'_iframe',:pid)'''),
                {'url': MENU_URL, 'sort': position, 'pid': parent})
            menu_id = result.lastrowid
            roles = connection.execute(text('SELECT DISTINCT role_id FROM ums_role_rights WHERE rights_id=:id'), {'id': anchor['id']}).scalars().all()
            for role in roles:
                connection.execute(text('INSERT INTO ums_role_rights (rights_id,role_id) VALUES (:id,:role)'), {'id': menu_id, 'role': role})
    return {'menu_id': menu_id, 'backup': backup}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--sqlite', type=Path)
    target.add_argument('--config', choices=['prod'])
    parser.add_argument('--backup-dir', type=Path, default=ROOT / 'instance' / 'receipt-migration-backups')
    args = parser.parse_args()
    if args.sqlite:
        uri = 'sqlite:///' + args.sqlite.resolve(strict=True).as_posix()
    else:
        from configs import config
        uri = config[args.config].SQLALCHEMY_DATABASE_URI
    engine = create_engine(uri)
    try:
        result = upgrade(engine, args.backup_dir)
        print(f"Receipt library ready: menu={result['menu_id']}, backup={result['backup']}")
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
