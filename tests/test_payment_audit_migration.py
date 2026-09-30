import unittest
from sqlalchemy import create_engine, text, inspect
from scripts.migrate_payment_audit import migrate


class PaymentAuditMigrationTest(unittest.TestCase):
    def test_existing_rows_are_preserved_and_migration_can_be_repeated(self):
        engine = create_engine('sqlite://')
        try:
            with engine.begin() as conn:
                conn.execute(text('CREATE TABLE ums_pay (id INTEGER PRIMARY KEY, handler VARCHAR(64), create_at DATETIME)'))
                conn.execute(text("INSERT INTO ums_pay VALUES (1, '历史经办人', '2023-08-04 00:00:00')"))
            self.assertEqual(len(migrate(engine)), 8)
            self.assertEqual(migrate(engine), [])
            self.assertIn('created_by_id', {c['name'] for c in inspect(engine).get_columns('ums_pay')})
            with engine.connect() as conn:
                row = conn.execute(text('SELECT * FROM ums_pay')).mappings().one()
                self.assertEqual(row['handler'], '历史经办人')
                self.assertEqual(row['create_at'], '2023-08-04 00:00:00')
                for key in ['generated_at', 'created_by_id', 'updated_by_id']:
                    self.assertIsNone(row[key])
        finally:
            engine.dispose()
