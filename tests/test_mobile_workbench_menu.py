import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class MobileWorkbenchMenuTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'menus.db'
        self.connection = sqlite3.connect(self.path)
        self.addCleanup(self.connection.close)
        self.connection.executescript('''
            CREATE TABLE ums_rights (
                id INTEGER PRIMARY KEY, name TEXT, code TEXT, type TEXT, url TEXT,
                icon_sign TEXT, status BOOLEAN, sort INTEGER, open_type TEXT, pid INTEGER
            );
            CREATE TABLE ums_role_rights (id INTEGER PRIMARY KEY, rights_id INTEGER, role_id INTEGER);
            INSERT INTO ums_rights (id,name,type,url,status,sort,pid) VALUES
                (124,'工作空间','menu',NULL,1,1,0),
                (125,'工作台','path','/view/console/index.html',1,2,124),
                (160,'其他菜单','path',NULL,1,3,0);
            INSERT INTO ums_role_rights (rights_id,role_id) VALUES (124,1),(125,2),(160,3);
        ''')
        self.connection.commit()

    def run_configuration(self):
        result = subprocess.run([
            sys.executable, str(ROOT / 'scripts' / 'configure_mobile_workbench.py'),
            '--sqlite', str(self.path), '--backup-dir', str(Path(self.directory.name) / 'backups'),
        ], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_repairs_existing_menu_without_changing_its_grants_or_disabled_state(self):
        self.connection.execute('''INSERT INTO ums_rights
            (id,name,type,url,status,sort,pid) VALUES (155,'移动端工作台','menu',NULL,0,4,124)''')
        self.connection.execute('INSERT INTO ums_role_rights (rights_id,role_id) VALUES (155,4)')
        self.connection.commit()
        self.run_configuration()
        self.assertEqual(self.connection.execute(
            'SELECT id,type,url,open_type,status,pid FROM ums_rights WHERE id=155'
        ).fetchone(), (155,'path','/m/','_blank',0,124))
        self.assertEqual(self.connection.execute(
            'SELECT role_id FROM ums_role_rights WHERE rights_id=155'
        ).fetchall(), [(4,)])
        self.assertIsNone(self.connection.execute('SELECT url FROM ums_rights WHERE id=160').fetchone()[0])
        backups = list((Path(self.directory.name) / 'backups').glob('*.json'))
        self.assertEqual(len(backups), 1)
        previous = json.loads(backups[0].read_text(encoding='utf-8'))
        self.assertIsNone(next(row for row in previous['ums_rights'] if row['id']==155)['url'])

    def test_missing_menu_inherits_only_workbench_navigation_grants_and_is_repeatable(self):
        self.run_configuration()
        row = self.connection.execute(
            "SELECT id,url,pid FROM ums_rights WHERE name='移动端工作台'"
        ).fetchone()
        self.assertEqual(row[1:], ('/m/',124))
        self.assertEqual(self.connection.execute(
            'SELECT role_id FROM ums_role_rights WHERE rights_id=? ORDER BY role_id', (row[0],)
        ).fetchall(), [(1,),(2,)])
        before = self.connection.execute('SELECT * FROM ums_role_rights ORDER BY id').fetchall()
        self.run_configuration()
        self.assertEqual(self.connection.execute(
            "SELECT id,url,pid FROM ums_rights WHERE name='移动端工作台'"
        ).fetchall(), [row])
        self.assertEqual(self.connection.execute('SELECT * FROM ums_role_rights ORDER BY id').fetchall(), before)


if __name__ == '__main__':
    unittest.main()
