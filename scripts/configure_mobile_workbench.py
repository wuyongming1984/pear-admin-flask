"""Configure the mobile workbench menu without starting Flask or cloud services."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
NAME = '移动端工作台'


def configure_menu(engine, backup_directory):
    with engine.begin() as connection:
        rows = connection.execute(text(
            "SELECT * FROM ums_rights WHERE name=:name AND type IN ('menu','path')"
        ), {'name': NAME}).mappings().all()
        for row in rows:
            if connection.execute(text(
                "SELECT id FROM ums_rights WHERE pid=:id AND type IN ('menu','path') LIMIT 1"
            ), {'id': row['id']}).first():
                raise ValueError('Mobile workbench is a directory with child menus')
        if rows and all(row['url']=='/m/' and row['type']=='path' and row['open_type']=='_blank' for row in rows):
            return [row['id'] for row in rows], None

        # Save the menu and grants before making a change; no user credentials are included.
        snapshot = {table: [dict(row) for row in connection.execute(text(
            f'SELECT * FROM {table} ORDER BY id'
        )).mappings()] for table in ('ums_rights', 'ums_role_rights')}
        directory = Path(backup_directory).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        backup = directory / f'mobile-workbench-{datetime.now():%Y%m%d-%H%M%S-%f}.json'
        with backup.open('x', encoding='utf-8') as output:
            json.dump(snapshot, output, ensure_ascii=False, indent=2)

        if rows:
            ids = [row['id'] for row in rows]
            for menu_id in ids:
                connection.execute(text(
                    "UPDATE ums_rights SET type='path',url='/m/',open_type='_blank' WHERE id=:id"
                ), {'id': menu_id})
        else:
            parent_id = connection.execute(text(
                "SELECT id FROM ums_rights WHERE name='工作空间' AND type='menu' ORDER BY id LIMIT 1"
            )).scalar() or 0
            roles = connection.execute(text('''
                SELECT DISTINCT rr.role_id FROM ums_role_rights rr
                JOIN ums_rights r ON r.id=rr.rights_id
                WHERE (r.id=:parent_id AND :parent_id<>0)
                   OR r.url='/view/console/index.html'
            '''), {'parent_id': parent_id}).scalars().all()
            result = connection.execute(text('''
                INSERT INTO ums_rights (name,code,type,url,icon_sign,status,sort,open_type,pid)
                VALUES (:name,'workspace:mobile','path','/m/',
                        'layui-icon layui-icon-cellphone',1,3,'_blank',:parent_id)
            '''), {'name': NAME, 'parent_id': parent_id})
            ids = [result.lastrowid]
            for role_id in roles:
                connection.execute(text(
                    'INSERT INTO ums_role_rights (rights_id,role_id) VALUES (:id,:role_id)'
                ), {'id': ids[0], 'role_id': role_id})
        return ids, backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--sqlite', type=Path, help='Existing local SQLite database')
    target.add_argument('--config', choices=['prod'], help='Explicit production database')
    parser.add_argument('--backup-dir', type=Path, default=ROOT / 'instance' / 'mobile-menu-backups')
    args = parser.parse_args()
    if args.sqlite:
        uri = 'sqlite:///' + args.sqlite.resolve(strict=True).as_posix()
    else:
        from configs import config
        uri = config[args.config].SQLALCHEMY_DATABASE_URI
    engine = create_engine(uri)
    try:
        ids, backup = configure_menu(engine, args.backup_dir)
        if backup:
            print(f'Menu backup: {backup}')
        print(f'Mobile workbench ready: ids={ids}, url=/m/, open_type=_blank')
    finally:
        engine.dispose()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Mobile menu configuration failed ({type(error).__name__}); '
              'check database access and menu hierarchy.', file=sys.stderr)
        raise SystemExit(1)
