import tempfile
import unittest
from pathlib import Path
from sqlalchemy import create_engine, text, inspect


class PaymentReceiptsMigrationTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.backups = Path(self.directory.name) / 'backups'
        self.engine = create_engine('sqlite:///' + (Path(self.directory.name) / 'repair.db').as_posix())
        self.addCleanup(self.engine.dispose)
        with self.engine.begin() as connection:
            connection.execute(text('CREATE TABLE ums_pay (id INTEGER PRIMARY KEY, pay_number TEXT)'))
            connection.execute(text("INSERT INTO ums_pay VALUES (1, 'KEEP')"))
            connection.execute(text('''CREATE TABLE ums_rights (id INTEGER PRIMARY KEY,
                name TEXT, code TEXT, type TEXT, url TEXT, icon_sign TEXT,
                status BOOLEAN, sort INTEGER, open_type TEXT, pid INTEGER)'''))
            connection.execute(text('CREATE TABLE ums_role_rights (id INTEGER PRIMARY KEY, rights_id INTEGER, role_id INTEGER)'))
            connection.execute(text('CREATE TABLE ums_user (id INTEGER PRIMARY KEY, username TEXT)'))
            connection.execute(text('CREATE TABLE ums_user_role (id INTEGER PRIMARY KEY, user_id INTEGER, role_id INTEGER)'))
            connection.execute(text("INSERT INTO ums_user VALUES (1, 'wym')"))
            connection.execute(text('INSERT INTO ums_user_role VALUES (1, 1, 7)'))

    def seed_server_menus(self, invoice_parent=0, order_parent=0):
        with self.engine.begin() as connection:
            connection.execute(text("INSERT INTO ums_rights VALUES (148, '发票详情库', 'material:invoice', 'path', '/view/material/invoice', '', 1, 3, '_component', :pid)"), {'pid': invoice_parent})
            connection.execute(text("INSERT INTO ums_rights VALUES (127, '订单付款管理', 'ums:order', 'menu', '', '', 1, 4, '_component', :pid)"), {'pid': order_parent})
            connection.execute(text("INSERT INTO ums_rights VALUES (156, '备份管理', '', 'path', '/system/views/backup.html', '', 1, 99, '_component', 100)"))
            connection.execute(text("INSERT INTO ums_rights VALUES (157, '移动端工作台', 'material:mobile', 'path', '/m/', '', 1, 99, '_blank', 146)"))
            connection.execute(text('INSERT INTO ums_role_rights VALUES (1, 148, 7)'))

    def test_repairs_existing_disabled_menu_without_changing_its_id_or_extra_grants(self):
        from scripts.migrate_payment_receipts import upgrade
        self.seed_server_menus()
        upgrade(self.engine, self.backups)
        with self.engine.begin() as connection:
            connection.execute(text("UPDATE ums_rights SET name='旧回单', type='auth', status=0, pid=146, sort=99 WHERE id=158"))
            connection.execute(text('DELETE FROM ums_role_rights WHERE rights_id=158'))
            connection.execute(text('INSERT INTO ums_role_rights VALUES (2, 158, 9)'))
        repaired = upgrade(self.engine, self.backups)
        with self.engine.connect() as connection:
            menu = connection.execute(text('SELECT name,type,status,pid,sort FROM ums_rights WHERE id=158')).one()
            self.assertEqual(tuple(menu), ('付款回单库', 'path', 1, 0, 4))
            self.assertEqual(connection.execute(text('SELECT role_id FROM ums_role_rights WHERE rights_id=158 ORDER BY role_id')).scalars().all(), [7, 9])
            self.assertEqual(connection.execute(text('SELECT pay_number FROM ums_pay')).scalar(), 'KEEP')
            self.assertEqual(connection.execute(text('SELECT name FROM ums_rights WHERE id=156')).scalar(), '备份管理')
        self.assertTrue(repaired['backup'].is_file())
        self.assertEqual(repaired['menu_id'], 158)
        self.assertIsNone(upgrade(self.engine, self.backups)['backup'])

    def test_recovers_removed_invoice_role_grant_on_an_otherwise_ready_menu(self):
        from scripts.migrate_payment_receipts import upgrade
        self.seed_server_menus()
        first = upgrade(self.engine, self.backups)
        with self.engine.begin() as connection:
            connection.execute(text('DELETE FROM ums_role_rights WHERE rights_id=158'))
        repaired = upgrade(self.engine, self.backups)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text('SELECT role_id FROM ums_role_rights WHERE rights_id=158')).scalars().all(), [7])
            self.assertEqual(connection.execute(text('SELECT sort FROM ums_rights WHERE id=127')).scalar(), 5)
        self.assertEqual(repaired['menu_id'], first['menu_id'])
        self.assertTrue(repaired['backup'].is_file())
        self.assertIsNone(upgrade(self.engine, self.backups)['backup'])

    def test_root_null_and_zero_siblings_keep_receipt_directly_after_invoice(self):
        from scripts.migrate_payment_receipts import upgrade
        self.seed_server_menus(invoice_parent=None, order_parent=0)
        upgrade(self.engine, self.backups)
        with self.engine.connect() as connection:
            self.assertIsNone(connection.execute(text('SELECT pid FROM ums_rights WHERE id=158')).scalar())
            self.assertEqual(connection.execute(text('SELECT id FROM ums_rights WHERE COALESCE(pid,0)=0 ORDER BY sort,id')).scalars().all(), [148, 158, 127])

    def test_check_reports_missing_grants_for_the_named_user_without_writing(self):
        from scripts.migrate_payment_receipts import upgrade, check
        self.seed_server_menus()
        upgrade(self.engine, self.backups)
        with self.engine.begin() as connection:
            connection.execute(text('DELETE FROM ums_role_rights WHERE rights_id=158'))
        before = list(self.backups.iterdir())
        report = check(self.engine, username='wym')
        self.assertFalse(report['ready'])
        self.assertEqual(report['missing_role_ids'], [7])
        self.assertFalse(report['user_receipt_visible'])
        self.assertEqual(list(self.backups.iterdir()), before)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text('SELECT COUNT(*) FROM ums_role_rights WHERE rights_id=158')).scalar(), 0)
        upgrade(self.engine, self.backups)
        self.assertTrue(check(self.engine, username='wym')['user_receipt_visible'])

    def test_user_visibility_matches_menu_api_for_a_granted_disabled_parent(self):
        from scripts.migrate_payment_receipts import upgrade, check
        self.seed_server_menus(invoice_parent=100, order_parent=100)
        with self.engine.begin() as connection:
            connection.execute(text("INSERT INTO ums_rights VALUES (100, '父菜单', '', 'menu', '', '', 0, 2, '', 0)"))
            connection.execute(text('INSERT INTO ums_role_rights VALUES (2, 100, 7)'))
        upgrade(self.engine, self.backups)
        self.assertTrue(check(self.engine, username='wym')['user_receipt_visible'])
        with self.engine.begin() as connection:
            connection.execute(text('DELETE FROM ums_role_rights WHERE rights_id=100'))
        self.assertFalse(check(self.engine, username='wym')['user_receipt_visible'])

    def test_keeps_receipt_adjacent_when_a_later_sibling_shares_invoice_sort(self):
        from scripts.migrate_payment_receipts import upgrade, check
        self.seed_server_menus()
        with self.engine.begin() as connection:
            connection.execute(text("INSERT INTO ums_rights VALUES (149, '同序菜单', '', 'path', '/same-sort', '', 1, 3, '', 0)"))
        upgrade(self.engine, self.backups)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text('SELECT id FROM ums_rights WHERE COALESCE(pid,0)=0 ORDER BY sort,id')).scalars().all(), [148, 158, 149, 127])
        self.assertTrue(check(self.engine)['ready'])
        self.assertIsNone(upgrade(self.engine, self.backups)['backup'])

    def test_root_menu_uses_null_when_legacy_zero_parent_has_no_referenced_row(self):
        from scripts.migrate_payment_receipts import upgrade
        with self.engine.begin() as connection:
            connection.execute(text('DROP TABLE ums_rights'))
            connection.execute(text('''CREATE TABLE ums_rights (id INTEGER PRIMARY KEY,
                name TEXT, code TEXT, type TEXT, url TEXT, icon_sign TEXT,
                status BOOLEAN, sort INTEGER, open_type TEXT, pid INTEGER REFERENCES ums_rights(id))'''))
        # Historical imports disable FK checks while inserting zero-parent root rows.
        self.seed_server_menus()
        with self.engine.connect() as connection:
            connection.execute(text('PRAGMA foreign_keys=ON'))
            connection.commit()
        upgraded = upgrade(self.engine, self.backups)
        with self.engine.connect() as connection:
            self.assertIsNone(connection.execute(text('SELECT pid FROM ums_rights WHERE id=158')).scalar())
            self.assertEqual(connection.execute(text('SELECT id FROM ums_rights WHERE COALESCE(pid,0)=0 ORDER BY sort,id')).scalars().all(), [148, 158, 127])
            self.assertEqual(connection.execute(text('PRAGMA foreign_keys')).scalar(), 1)
        self.assertEqual(upgraded['menu_id'], 158)
        self.assertIsNone(upgrade(self.engine, self.backups)['backup'])

    def test_adds_only_receipt_tables_and_inherits_invoice_menu_grants_once(self):
        from scripts.migrate_payment_receipts import upgrade
        with tempfile.TemporaryDirectory() as directory:
            engine = create_engine('sqlite:///' + (Path(directory) / 'test.db').as_posix())
            with engine.begin() as connection:
                connection.execute(text('CREATE TABLE ums_pay (id INTEGER PRIMARY KEY, pay_number TEXT)'))
                connection.execute(text("INSERT INTO ums_pay VALUES (1, 'KEEP')"))
                connection.execute(text('''CREATE TABLE ums_rights (id INTEGER PRIMARY KEY,
                    name TEXT, code TEXT, type TEXT, url TEXT, icon_sign TEXT,
                    status BOOLEAN, sort INTEGER, open_type TEXT, pid INTEGER)'''))
                connection.execute(text('CREATE TABLE ums_role_rights (id INTEGER PRIMARY KEY, rights_id INTEGER, role_id INTEGER)'))
                connection.execute(text("INSERT INTO ums_rights VALUES (2, '发票详情库', 'invoice', 'path', '/view/material/invoice', '', 1, 5, '_iframe', 1)"))
                connection.execute(text("INSERT INTO ums_rights VALUES (3, '后续菜单', 'other', 'path', '/other', '', 1, 6, '_iframe', 1)"))
                connection.execute(text('INSERT INTO ums_role_rights VALUES (1, 2, 7)'))
            first = upgrade(engine, Path(directory) / 'backups')
            second = upgrade(engine, Path(directory) / 'backups')
            self.assertTrue(first['backup'].is_file())
            self.assertIsNone(second['backup'])
            self.assertTrue({'payment_receipt', 'pay_receipt_relation'} <= set(inspect(engine).get_table_names()))
            with engine.connect() as connection:
                self.assertEqual(connection.execute(text('SELECT pay_number FROM ums_pay')).scalar(), 'KEEP')
                menus = connection.execute(text('SELECT name FROM ums_rights WHERE pid=1 ORDER BY sort,id')).scalars().all()
                self.assertEqual(menus, ['发票详情库', '付款回单库', '后续菜单'])
                roles = connection.execute(text('SELECT role_id FROM ums_role_rights WHERE rights_id=:id'), {'id': first['menu_id']}).scalars().all()
                self.assertEqual(roles, [7])
            engine.dispose()
