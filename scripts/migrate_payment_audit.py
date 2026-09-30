"""Add payment audit columns without fabricating historical audit values.

Local: python scripts/migrate_payment_audit.py --sqlite instance/pear_admin.db
Server (after backup): python scripts/migrate_payment_audit.py --config prod
Does not initialize the application, scheduler or cloud storage.
"""
import argparse
from pathlib import Path
import sqlite3
import sys
from datetime import datetime

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.schema import CreateColumn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def migrate(engine):
    from pear_admin.orms import PayORM

    names = (
        'generated_at', 'created_by_id', 'created_by_username', 'created_by_nickname',
        'updated_at', 'updated_by_id', 'updated_by_username', 'updated_by_nickname',
    )
    existing = {column['name'] for column in inspect(engine).get_columns('ums_pay')}
    added = []
    with engine.begin() as connection:
        for name in names:
            if name in existing:
                continue
            column = str(CreateColumn(PayORM.__table__.c[name]).compile(dialect=engine.dialect))
            connection.execute(text(f'ALTER TABLE ums_pay ADD COLUMN {column}'))
            added.append(name)
    return added


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--sqlite', type=Path, help='Existing local SQLite database; backed up automatically')
    target.add_argument('--config', choices=['prod'], help='Explicit production database; back up first')
    args = parser.parse_args()
    if args.sqlite:
        path = args.sqlite.resolve(strict=True)
        backup = path.with_name(path.name + '.payment-audit-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.bak')
        with sqlite3.connect(path) as source, sqlite3.connect(backup) as destination:
            source.backup(destination)
        print(f'Backup: {backup}')
        uri = 'sqlite:///' + path.as_posix()
    else:
        from configs import config
        uri = config[args.config].SQLALCHEMY_DATABASE_URI
    engine = create_engine(uri)
    try:
        print('Added: ' + ', '.join(migrate(engine)))
        print('Payment audit schema ready; historical values left unknown.')
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
