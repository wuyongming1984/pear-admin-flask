import unittest
from contextlib import closing
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import create_engine, text, inspect
from scripts import migrate_payment_audit as migration
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

    def test_upgrade_backs_up_old_schema_and_rows_before_adding_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'existing.db'
            engine = create_engine('sqlite:///' + path.as_posix())
            try:
                with engine.begin() as conn:
                    conn.execute(text('CREATE TABLE ums_pay (id INTEGER PRIMARY KEY, handler VARCHAR(64), create_at DATETIME)'))
                    conn.execute(text("INSERT INTO ums_pay VALUES (1, '历史经办人', '2023-08-04 00:00:00')"))
                added, backup = migration.upgrade(engine, Path(directory) / 'backups')
                self.assertEqual(len(added), 8)
                with closing(sqlite3.connect(backup)) as conn:
                    self.assertEqual(conn.execute('SELECT * FROM ums_pay').fetchone(),
                                     (1, '历史经办人', '2023-08-04 00:00:00'))
                    self.assertNotIn('generated_at', {row[1] for row in conn.execute('PRAGMA table_info(ums_pay)')})
                with engine.connect() as conn:
                    row = conn.execute(text('SELECT * FROM ums_pay')).mappings().one()
                    self.assertEqual(row['handler'], '历史经办人')
                    self.assertIsNone(row['generated_at'])
                self.assertEqual(migration.upgrade(engine, Path(directory) / 'backups'), ([], None))
                self.assertEqual(len(list((Path(directory) / 'backups').iterdir())), 1)
            finally:
                engine.dispose()

    def test_backup_failure_stops_before_any_schema_change(self):
        engine = create_engine('sqlite://')
        try:
            with engine.begin() as conn:
                conn.execute(text('CREATE TABLE ums_pay (id INTEGER PRIMARY KEY, handler VARCHAR(64))'))
                conn.execute(text("INSERT INTO ums_pay VALUES (1, '原经办人')"))
            with patch.object(migration, 'backup_database', create=True, side_effect=RuntimeError('backup failed')):
                with self.assertRaisesRegex(RuntimeError, 'backup failed'):
                    migration.upgrade(engine, Path('unused-backup-directory'))
            self.assertEqual({column['name'] for column in inspect(engine).get_columns('ums_pay')}, {'id', 'handler'})
            with engine.connect() as conn:
                self.assertEqual(conn.execute(text('SELECT handler FROM ums_pay')).scalar(), '原经办人')
        finally:
            engine.dispose()

    def test_mysql_backup_targets_configured_database_and_keeps_password_out_of_arguments(self):
        engine = create_engine('mysql+pymysql://backup_user:test-secret@database.example:3307/business')
        try:
            with tempfile.TemporaryDirectory() as directory:
                def dump(command, **kwargs):
                    self.assertEqual(command[-2:], ['business', 'ums_pay'])
                    self.assertIn('--host=database.example', command)
                    self.assertIn('--port=3307', command)
                    self.assertIn('--single-transaction', command)
                    self.assertIn('--no-tablespaces', command)
                    self.assertNotIn('test-secret', ' '.join(command))
                    self.assertEqual(kwargs['env']['MYSQL_PWD'], 'test-secret')
                    kwargs['stdout'].write(b'CREATE TABLE ums_pay (id INT);\nINSERT INTO ums_pay VALUES (1);\n')
                    return subprocess.CompletedProcess(command, 0)
                with patch.object(migration.shutil, 'which', return_value='dump-tool'), \
                        patch.object(migration.subprocess, 'run', side_effect=dump):
                    backup = migration.backup_database(engine, Path(directory))
                self.assertIn('INSERT INTO ums_pay VALUES (1)', backup.read_text())
                self.assertEqual(list(Path(directory).iterdir()), [backup])
        finally:
            engine.dispose()

    def test_failed_mysql_dump_cannot_be_mistaken_for_a_valid_backup(self):
        engine = create_engine('mysql+pymysql://backup_user:test-secret@database.example/business')
        try:
            with tempfile.TemporaryDirectory() as directory:
                def failed_dump(command, **kwargs):
                    kwargs['stdout'].write(b'incomplete dump')
                    return subprocess.CompletedProcess(command, 1)
                with patch.object(migration.shutil, 'which', return_value='dump-tool'), \
                        patch.object(migration.subprocess, 'run', side_effect=failed_dump):
                    with self.assertRaisesRegex(RuntimeError, 'backup failed'):
                        migration.backup_database(engine, Path(directory))
                self.assertEqual(list(Path(directory).iterdir()), [])
        finally:
            engine.dispose()
