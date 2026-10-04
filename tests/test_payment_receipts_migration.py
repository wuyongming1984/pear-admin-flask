import tempfile
import unittest
from pathlib import Path
from sqlalchemy import create_engine, text, inspect


class PaymentReceiptsMigrationTest(unittest.TestCase):
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
