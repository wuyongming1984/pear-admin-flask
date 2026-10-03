"""Old deployment schema and the server update's read-only API gate."""
import json
import sqlite3
import unittest
from contextlib import closing, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from pear_admin.extensions import db
from scripts import migrate_payment_audit, profile_editor_queries
from tests import test_document_workspace


class DocumentSchemaUpgradeTest(unittest.TestCase):
    setUp = test_document_workspace.DocumentWorkspaceTest.setUp
    tearDown = test_document_workspace.DocumentWorkspaceTest.tearDown
    seed = test_document_workspace.DocumentWorkspaceTest.seed

    def test_old_payment_schema_upgrade_restores_desktop_and_mobile_lists(self):
        self.seed(count=2)
        columns = ('generated_at', 'created_by_id', 'created_by_username', 'created_by_nickname',
                   'updated_at', 'updated_by_id', 'updated_by_username', 'updated_by_nickname')
        db.session.remove()
        with db.engine.begin() as conn:
            for name in columns:
                conn.execute(text('ALTER TABLE ums_pay DROP COLUMN ' + name))
        paths = ('/api/v1/workspace/orders', '/api/v1/workspace/payments',
                 '/api/v1/order/?limit=3&page=1', '/api/v1/pay/?limit=3&page=1')
        for path in paths:
            db.session.remove()
            with self.assertRaisesRegex(OperationalError, 'no such column: ums_pay.generated_at'):
                self.client.get(path, headers=self.headers)
        db.session.remove()
        added, backup = migrate_payment_audit.upgrade(db.engine, Path(self.temp.name) / 'backups')
        self.assertEqual(len(added), 8)
        with closing(sqlite3.connect(backup)) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM ums_pay').fetchone()[0], 2)
            self.assertNotIn('generated_at', {row[1] for row in conn.execute('PRAGMA table_info(ums_pay)')})
        for path in paths:
            db.session.remove()
            response = self.client.get(path, headers=self.headers)
            self.assertEqual(response.status_code, 200, path)
            self.assertEqual(response.json['code'], 0, path)
            self.assertEqual(response.json['count'], 2, path)
        self.assertEqual(migrate_payment_audit.upgrade(db.engine, Path(self.temp.name) / 'backups'), ([], None))

    def run_probe(self):
        output = StringIO()
        with patch('sys.argv', ['profile_editor_queries.py', '--config', 'prod', '--scope', 'documents']), \
                patch.object(profile_editor_queries, 'create_diagnostic_app', return_value=self.app), \
                redirect_stdout(output):
            profile_editor_queries.main()
        return [json.loads(line) for line in output.getvalue().splitlines()]

    def test_document_probe_checks_real_desktop_and_mobile_endpoints(self):
        self.seed(count=2)
        results = self.run_probe()[1:]
        self.assertEqual(len(results), 4)
        self.assertEqual({result['path'] for result in results},
                         {'/workspace/orders?page=1&limit=20', '/workspace/payments?page=1&limit=20',
                          '/order/?page=1&limit=3', '/pay/?page=1&limit=3'})
        for result in results:
            self.assertEqual(result['status'], 200)
            self.assertEqual(result['code'], 0)
            self.assertEqual(result['total_rows'], 2)

    def test_document_probe_stops_on_http_or_business_error(self):
        self.seed(count=2)
        endpoint = next(rule.endpoint for rule in self.app.url_map.iter_rules()
                        if rule.rule == '/api/v1/workspace/orders')
        for status in (200, 500):
            with self.subTest(status=status), \
                    patch.dict(self.app.view_functions, {endpoint: lambda: ({'code': -1}, status)}):
                with self.assertRaisesRegex(RuntimeError, 'API check failed'):
                    self.run_probe()
