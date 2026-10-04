"""Use synthetic batches and disposable databases; never connect to production."""
import copy
from datetime import date
from decimal import Decimal
import gzip
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from cryptography.fernet import Fernet
from sqlalchemy import create_engine, event, insert, select

from pear_admin.extensions import db
from pear_admin.orms import MaterialInvoiceORM, MaterialInvoiceDetailORM
from pear_admin.orms.pay import pay_invoice_relation
from scripts import import_tax_invoices as importer


class EncryptedBatchTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.key = Fernet.generate_key()
        self.key_file = self.root / "batch.key"
        self.key_file.write_bytes(self.key + b"\n")
        self.payload_file = self.root / "batch.fernet"
        plaintext = gzip.compress(json.dumps({"source_filename": "synthetic.xlsx", "records": []}).encode())
        self.payload_file.write_bytes(Fernet(self.key).encrypt(plaintext))

    def test_decrypts_the_supplied_file_with_a_separate_key(self):
        try:
            result = importer.load_payload(self.payload_file, self.key_file)
        except Exception as exc:
            self.fail(f"The encrypted batch could not be loaded: {exc}")
        self.assertEqual(result, {"source_filename": "synthetic.xlsx", "records": []})

    def test_wrong_key_is_rejected(self):
        self.key_file.write_bytes(Fernet.generate_key())
        with self.assertRaisesRegex(RuntimeError, "解密失败"):
            importer.load_payload(self.payload_file, self.key_file)

    def test_modified_payload_is_rejected(self):
        token = bytearray(self.payload_file.read_bytes())
        token[len(token) // 2] = ord("A") if token[len(token) // 2] != ord("A") else ord("B")
        self.payload_file.write_bytes(token)
        with self.assertRaisesRegex(RuntimeError, "解密失败"):
            importer.load_payload(self.payload_file, self.key_file)

    def test_cli_rejects_wrong_key_before_initializing_database(self):
        self.key_file.write_bytes(Fernet.generate_key())
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(Path(importer.__file__)), "--payload", str(self.payload_file),
             "--key-file", str(self.key_file), "--preview"],
            cwd=self.root, capture_output=True, encoding="utf-8",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("解密失败", result.stderr)
        self.assertNotIn("SQLAlchemy", result.stderr)


def synthetic_record(number, net="100.00", tax="0.00"):
    return {
        "row": 2, "status": "new", "invoice_number": number, "invoice_code": "",
        "warnings": [],
        "values": {
            "invoice_number": number, "invoice_code": "", "invoice_date": "2026-01-03",
            "buyer_name": "测试购方", "buyer_tax_num": "BUYER", "seller_name": "测试售方",
            "seller_tax_num": "SELLER", "total_amount": net, "tax_amount": tax,
            "ocr_status": "imported",
            "ocr_result": json.dumps({"tax_excel": {"source_row": 2, "status": "正常"}}),
        },
        "details": [{"name": "测试服务", "spec": "", "unit": "次", "quantity": "1.0000",
                     "price": net, "amount": net, "tax_rate": "免税", "tax_amount": tax}],
    }


class ImportTransactionTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.engine = create_engine("sqlite://")
        self.addCleanup(self.engine.dispose)
        db.metadata.create_all(self.engine)
        self.invoices = MaterialInvoiceORM.__table__
        self.details = MaterialInvoiceDetailORM.__table__
        self.existing_number = "26000000000000000001"
        self.new_number = "26000000000000000002"
        old = synthetic_record(self.existing_number)["values"]
        old.update(id=1, invoice_date=date(2026, 1, 3), total_amount=Decimal("100.00"),
                   tax_amount=Decimal("0.00"), project_id=42, supplier_id=7,
                   file_path="/uploads/original.pdf", invoice_category="原分类", remarks="原备注")
        with self.engine.begin() as conn:
            conn.execute(insert(self.invoices), old)
            conn.execute(insert(self.details), {"invoice_id": 1, "name": "原明细", "amount": Decimal("100.00")})
            conn.execute(insert(pay_invoice_relation), {"pay_id": 9, "invoice_id": 1})
        self.before = self.snapshot()
        self.payload = {
            "batch_id": "synthetic", "source_filename": "synthetic.xlsx", "source_sha256": "0" * 64,
            "invoice_count": 2, "source_totals": {"net": "80.00", "tax": "0.00", "gross": "80.00"},
            "expected_existing": [{"id": 1, "invoice_number": self.existing_number, "invoice_code": ""}],
            "records": [synthetic_record(self.existing_number), synthetic_record(self.new_number, "-20.00")],
        }

    def snapshot(self):
        with self.engine.connect() as conn:
            return [[dict(r) for r in conn.execute(select(t).order_by(*t.primary_key.columns)).mappings()]
                    for t in (self.invoices, self.details, pay_invoice_relation)]

    def run_batch(self, commit=False):
        return importer.run_import(self.engine, self.invoices, self.details, pay_invoice_relation,
                                   self.payload, self.root / "audit", commit=commit, allow_local_test=True)

    def test_preview_does_not_write_and_reports_duplicates(self):
        result = self.run_batch()
        self.assertEqual((result["existing_skipped"], result["new_invoices"], result["new_details"]), (1, 1, 1))
        self.assertEqual(result["existing_amount_differences"], 0)
        self.assertFalse(result["committed"])
        self.assertEqual(self.snapshot(), self.before)

    def test_import_preserves_existing_links_and_negative_amount_then_adds_zero_on_repeat(self):
        result = self.run_batch(commit=True)
        self.assertEqual(result["imported"], 1)
        self.assertTrue(result["committed"])
        after = self.snapshot()
        self.assertEqual(after[0][0], self.before[0][0])
        self.assertEqual(after[1][0], self.before[1][0])
        self.assertEqual(after[2], self.before[2])
        self.assertEqual(after[0][1]["total_amount"], Decimal("-20.00"))
        self.assertEqual(after[1][1]["amount"], Decimal("-20.00"))
        repeated = self.run_batch(commit=True)
        self.assertEqual(repeated["imported"], 0)
        self.assertEqual(self.snapshot(), after)
        self.assertTrue((Path(result["audit_directory"]) / "before-backup.json").is_file())

    def test_incorrect_amount_aborts_and_rolls_back_all_writes(self):
        injected = []
        def corrupt_insert(conn, cursor, statement, parameters, context, executemany):
            if not injected and statement.startswith("INSERT INTO material_invoice ("):
                injected.append(True)
                conn.exec_driver_sql("UPDATE material_invoice SET total_amount = 999 WHERE id = ?", (cursor.lastrowid,))
        event.listen(self.engine, "after_cursor_execute", corrupt_insert)
        try:
            with self.assertRaisesRegex(RuntimeError, "回滚"):
                self.run_batch(commit=True)
        finally:
            event.remove(self.engine, "after_cursor_execute", corrupt_insert)
        self.assertTrue(injected)
        self.assertEqual(self.snapshot(), self.before)

    def test_different_target_database_is_rejected(self):
        self.payload["expected_existing"][0]["id"] = 999
        with self.assertRaisesRegex(RuntimeError, "目标数据库"):
            self.run_batch(commit=True)
        self.assertEqual(self.snapshot(), self.before)

    def test_duplicate_source_identity_is_rejected(self):
        self.payload["records"][1] = copy.deepcopy(self.payload["records"][0])
        with self.assertRaisesRegex(RuntimeError, "唯一票号"):
            self.run_batch(commit=True)
        self.assertEqual(self.snapshot(), self.before)

    def test_sqlite_is_rejected_without_explicit_test_opt_in(self):
        with self.assertRaisesRegex(RuntimeError, "MySQL"):
            importer.run_import(self.engine, self.invoices, self.details, pay_invoice_relation,
                                self.payload, self.root / "audit", commit=True)
        self.assertEqual(self.snapshot(), self.before)


if __name__ == "__main__":
    unittest.main()
