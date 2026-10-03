"""Add payment audit columns without fabricating historical audit values.

Local: python scripts/migrate_payment_audit.py --sqlite instance/pear_admin.db
Server (automatic payment-table backup): python scripts/migrate_payment_audit.py --config prod
Does not initialize the application, scheduler or cloud storage.
"""
import argparse
from contextlib import closing
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.schema import CreateColumn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

AUDIT_COLUMNS = (
    'generated_at', 'created_by_id', 'created_by_username', 'created_by_nickname',
    'updated_at', 'updated_by_id', 'updated_by_username', 'updated_by_nickname',
)


def missing_columns(engine):
    existing = {column['name'] for column in inspect(engine).get_columns('ums_pay')}
    return [name for name in AUDIT_COLUMNS if name not in existing]


def backup_database(engine, directory):
    """Save a restorable backup before DDL, outside the image on the /app mount."""
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    sqlite = engine.dialect.name == 'sqlite'
    backup = directory / f'ums_pay.payment-audit-{stamp}.{"db" if sqlite else "sql"}'
    partial = backup.with_suffix(backup.suffix + '.partial')
    try:
        if sqlite:
            with engine.connect() as connection, closing(sqlite3.connect(partial)) as destination:
                os.chmod(partial, 0o600)
                connection.connection.driver_connection.backup(destination)
        elif engine.dialect.name in ('mysql', 'mariadb'):
            executable = shutil.which('mariadb-dump') or shutil.which('mysqldump')
            if not executable:
                raise RuntimeError('mariadb-dump or mysqldump is required; schema was not changed')
            url = engine.url
            command = [executable, '--single-transaction', '--no-tablespaces', '--skip-lock-tables',
                       '--hex-blob', '--default-character-set=utf8mb4', '--protocol=tcp',
                       f'--host={url.host}', f'--port={url.port or 3306}', f'--user={url.username}',
                       url.database, 'ums_pay']
            environment = os.environ.copy()
            environment['MYSQL_PWD'] = url.password or ''
            with partial.open('xb') as output:
                os.chmod(partial, 0o600)
                result = subprocess.run(command, env=environment, stdout=output,
                                        stderr=subprocess.PIPE, timeout=300)
            if result.returncode != 0 or partial.stat().st_size == 0:
                raise RuntimeError('Payment backup failed; schema was not changed')
        else:
            raise RuntimeError('Unsupported database; schema was not changed')
        partial.replace(backup)
        return backup
    except BaseException:
        partial.unlink(missing_ok=True)
        raise


def upgrade(engine, backup_directory):
    if not missing_columns(engine):
        return [], None
    backup = backup_database(engine, backup_directory)
    added = migrate(engine)
    if missing_columns(engine):
        raise RuntimeError('Payment audit fields are still missing after migration')
    return added, backup


def migrate(engine):
    from pear_admin.orms import PayORM

    names = missing_columns(engine)
    added = []
    with engine.begin() as connection:
        for name in names:
            column = str(CreateColumn(PayORM.__table__.c[name]).compile(dialect=engine.dialect))
            connection.execute(text(f'ALTER TABLE ums_pay ADD COLUMN {column}'))
            added.append(name)
    return added


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--sqlite', type=Path, help='Existing local SQLite database; backed up automatically')
    target.add_argument('--config', choices=['prod'], help='Explicit production database; payment table backed up automatically')
    parser.add_argument('--backup-dir', type=Path, default=ROOT / 'instance' / 'payment-audit-backups')
    args = parser.parse_args()
    if args.sqlite:
        path = args.sqlite.resolve(strict=True)
        uri = 'sqlite:///' + path.as_posix()
    else:
        from configs import config
        uri = config[args.config].SQLALCHEMY_DATABASE_URI
    engine = create_engine(uri)
    try:
        added, backup = upgrade(engine, args.backup_dir)
        if backup:
            print(f'Backup: {backup}', flush=True)
        print('Added: ' + (', '.join(added) if added else '(none; schema already ready)'))
        print('Payment audit schema ready; historical values left unknown.')
    finally:
        engine.dispose()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Driver/subprocess errors can include connection details. Keep them private.
        print(f'Payment audit upgrade failed ({type(error).__name__}); check database access, '
              'dump utility and backup permissions. Update stopped.', file=sys.stderr)
        raise SystemExit(1)
