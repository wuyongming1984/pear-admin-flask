#!/usr/bin/env python3
"""Import a prepared, encrypted tax export into the Pear invoice database.

Run inside the existing web container, from /app. Defaults to preview only.
The repository contains only encrypted invoice data; provide the key separately.
The existing cryptography dependency is sufficient; Excel is not needed on server.
"""
import argparse
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
import gzip
import getpass
import json
import os
from pathlib import Path
import re
import sys
import unicodedata

DEFAULT_PAYLOAD = Path(__file__).resolve().parent / "invoice_batches" / "20261004.fernet"


def load_payload(payload_path=DEFAULT_PAYLOAD, key_file=None):
    """Authenticate and decrypt the batch before initializing any database."""
    from cryptography.fernet import Fernet, InvalidToken

    try:
        encrypted = Path(payload_path).read_bytes()
    except OSError:
        raise RuntimeError("无法读取加密数据包，请先拉取本次导入代码") from None
    if key_file:
        try:
            key = Path(key_file).read_text(encoding="ascii").strip()
        except (OSError, UnicodeError):
            raise RuntimeError("无法读取解密密钥文件") from None
    else:
        try:
            key = getpass.getpass("请输入本批次解密密钥（输入不回显）：").strip()
        except EOFError:
            raise RuntimeError("请交互输入解密密钥，或用 --key-file 指定仓库外的密钥文件") from None
    try:
        decrypted = Fernet(key.encode("ascii")).decrypt(encrypted)
    except (InvalidToken, ValueError, UnicodeError):
        raise RuntimeError("解密失败：密钥不正确或数据包被改动；未连接数据库") from None
    try:
        return json.loads(gzip.decompress(decrypted))
    except (OSError, UnicodeError, ValueError):
        raise RuntimeError("解密后的数据格式无效；未连接数据库") from None


def clean(value):
    return "" if value is None or str(value).strip() in ("", "--", "-", "无") else str(value).strip()


def identity(number, code=None):
    number = clean(number)
    return ("", number) if len(number) == 20 and number.isdigit() else (clean(code), number)


def matching(rows, number, code):
    key = identity(number, code)
    exact = [r for r in rows if identity(r["invoice_number"], r["invoice_code"]) == key]
    return exact or [r for r in rows if clean(r["invoice_number"]) == key[1]
                     and (not key[0] or not clean(r["invoice_code"]))]


def normalized(value):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str("" if value is None else value))).upper()


def review_existing(record, existing):
    labels = {"total_amount": "不含税金额", "tax_amount": "税额", "invoice_date": "开票日期",
              "buyer_name": "购买方名称", "seller_name": "销售方名称",
              "buyer_tax_num": "购买方税号", "seller_tax_num": "销售方税号"}
    differences, missing = [], []
    for row in existing:
        for field, label in labels.items():
            source, current = record["values"].get(field), row.get(field)
            if not normalized(current):
                if normalized(source):
                    missing.append({"existing_id": row["id"], "field": label})
                continue
            if not normalized(source):
                continue
            same = (Decimal(str(current)).quantize(Decimal(".01")) == Decimal(str(source)).quantize(Decimal(".01"))
                    if field in ("total_amount", "tax_amount") else normalized(current) == normalized(source))
            if not same:
                differences.append({"existing_id": row["id"], "field": label,
                                    "excel": str(source), "online": str(current)})
    exact_identity = all(identity(row["invoice_number"], row["invoice_code"]) == identity(record["invoice_number"], record.get("invoice_code")) for row in existing)
    return {"source_row": record["row"], "invoice_number": record["invoice_number"],
            "existing_ids": [r["id"] for r in existing], "action": "保留线上记录，跳过导入",
            "identity_exact": exact_identity, "ambiguous": len(existing) != 1,
            "needs_review": bool(differences) or not exact_identity or len(existing) != 1,
            "differences": differences, "missing_online": missing}


def write_json(path, content):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(content, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def totals(rows):
    net = sum((Decimal(str(r["total_amount"] or 0)) for r in rows), Decimal(0))
    tax = sum((Decimal(str(r["tax_amount"] or 0)) for r in rows), Decimal(0))
    return {"net": str(net.quantize(Decimal(".01"))),
            "tax": str(tax.quantize(Decimal(".01"))),
            "gross": str((net + tax).quantize(Decimal(".01")))}


def run_import(engine, invoice_table, detail_table, relation_table, payload, output_root,
               commit=False, allow_local_test=False):
    """Use one transaction; verify both inserted rows and untouched records."""
    from sqlalchemy import insert, select, text

    if engine.dialect.name != "mysql" and not allow_local_test:
        raise RuntimeError("正式导入要求 MySQL；本次未写入任何数据")
    records = payload["records"]
    keys = [identity(r["invoice_number"], r.get("invoice_code")) for r in records]
    if len(records) != payload["invoice_count"] or len(set(keys)) != len(keys):
        raise RuntimeError("导入数据数量或唯一票号校验失败")
    if any(r["status"] != "new" or not r.get("details") for r in records):
        raise RuntimeError("导入数据包含无效记录或缺失明细")
    if totals([r["values"] for r in records]) != payload["source_totals"]:
        raise RuntimeError("导入数据金额校验失败")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    audit_dir = Path(output_root) / timestamp
    audit_dir.mkdir(parents=True, exist_ok=False)
    os.chmod(audit_dir, 0o700)
    live_engine = engine.execution_options(isolation_level="SERIALIZABLE") if commit and engine.dialect.name == "mysql" else engine

    with live_engine.connect() as connection:
        with connection.begin():
            if engine.dialect.name == "mysql":
                connection.execute(text("SET SESSION innodb_lock_wait_timeout = 15"))
                engines = dict(connection.execute(text(
                    "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN "
                    "('material_invoice','material_invoice_detail','pay_invoice_relation')"
                )).all())
                if set(engines) != {invoice_table.name, detail_table.name, relation_table.name} or any(str(e).upper() != "INNODB" for e in engines.values()):
                    raise RuntimeError("发票表必须使用 InnoDB 事务，本次未写入数据")

            def snapshot(table):
                statement = select(table).order_by(*table.primary_key.columns)
                if commit:
                    statement = statement.with_for_update()
                return [dict(row) for row in connection.execute(statement).mappings()]

            before_invoices = snapshot(invoice_table)
            before_details = snapshot(detail_table)
            before_relations = snapshot(relation_table)
            by_id = {r["id"]: r for r in before_invoices}
            # Confirm this is the same formal database observed through its API.
            for expected in payload["expected_existing"]:
                actual = by_id.get(expected["id"])
                if not actual or identity(actual["invoice_number"], actual["invoice_code"]) != identity(expected["invoice_number"], expected["invoice_code"]):
                    raise RuntimeError("与正式站点查重快照不一致，请重新核对目标数据库；未写入数据")

            by_number = defaultdict(list)
            for row in before_invoices:
                by_number[clean(row["invoice_number"])].append(row)
            new, skipped = [], []
            for record in records:
                existing = matching(by_number[record["invoice_number"]], record["invoice_number"], record.get("invoice_code"))
                if existing:
                    skipped.append(review_existing(record, existing))
                else:
                    new.append(record)
            report = {
                "mode": "import" if commit else "preview",
                "source_filename": payload["source_filename"],
                "source_sha256": payload["source_sha256"],
                "source_invoices": len(records),
                "before_count": len(before_invoices),
                "existing_skipped": len(skipped),
                "existing_need_review": sum(r["needs_review"] for r in skipped),
                "existing_amount_differences": sum(any(d["field"] in ("不含税金额", "税额") for d in r["differences"]) for r in skipped),
                "existing_with_missing_fields": sum(bool(r["missing_online"]) for r in skipped),
                "new_invoices": len(new),
                "new_details": sum(len(r["details"]) for r in new),
                "new_totals": totals([r["values"] for r in new]),
                "warnings": [{"source_row": r["row"], "invoice_number": r["invoice_number"], "messages": r["warnings"]}
                             for r in new if r["warnings"]],
                "expected_final_count": len(before_invoices) + len(new),
                "audit_directory": str(audit_dir),
                "imported": 0,
                "committed": False,
            }
            write_json(audit_dir / "skipped-existing.json", skipped)
            if not commit:
                write_json(audit_dir / "preview.json", report)
                return report

            # A write failure here aborts before any invoice is inserted.
            write_json(audit_dir / "before-backup.json", {
                "source_sha256": payload["source_sha256"],
                invoice_table.name: before_invoices,
                detail_table.name: before_details,
                relation_table.name: before_relations,
            })
            new_by_id, detail_rows = {}, []
            for record in new:
                values = dict(record["values"])
                values["invoice_date"] = date.fromisoformat(values["invoice_date"])
                for field in ("total_amount", "tax_amount"):
                    values[field] = Decimal(values[field])
                metadata = json.loads(values["ocr_result"])
                metadata["tax_excel"].update(import_batch=payload["batch_id"], source_sha256=payload["source_sha256"])
                values["ocr_result"] = json.dumps(metadata, ensure_ascii=False)
                if len(values["ocr_result"].encode("utf-8")) > 65535:
                    raise RuntimeError("发票原始数据超过现有数据库字段容量；本次导入已回滚")
                values["project_id"] = None
                inserted = connection.execute(insert(invoice_table).values(**values))
                invoice_id = inserted.inserted_primary_key[0]
                new_by_id[invoice_id] = record
                for detail in record["details"]:
                    detail = dict(detail)
                    for field in ("quantity", "price", "amount", "tax_amount"):
                        if detail[field] is not None:
                            detail[field] = Decimal(detail[field])
                    detail_rows.append(dict(invoice_id=invoice_id, **detail))
            # Bounded batches also work within MySQL's packet limit.
            for start in range(0, len(detail_rows), 500):
                connection.execute(insert(detail_table), detail_rows[start:start + 500])
            after_invoices = snapshot(invoice_table)
            after_details = snapshot(detail_table)
            after_relations = snapshot(relation_table)
            after_by_id = {r["id"]: r for r in after_invoices}
            after_detail_by_id = {r["id"]: r for r in after_details}
            if any(after_by_id.get(r["id"]) != r for r in before_invoices):
                raise RuntimeError("已有发票发生变化，导入已回滚")
            if any(after_detail_by_id.get(r["id"]) != r for r in before_details) or after_relations != before_relations:
                raise RuntimeError("已有明细或付款关联发生变化，导入已回滚")
            if len(after_invoices) != report["expected_final_count"] or len(after_details) != len(before_details) + len(detail_rows):
                raise RuntimeError("导入数量不一致，导入已回滚")
            actual_new = [after_by_id[i] for i in new_by_id]
            if totals(actual_new) != report["new_totals"]:
                raise RuntimeError("导入金额不一致，导入已回滚")
            details_by_invoice = defaultdict(list)
            for detail in after_details:
                if detail["invoice_id"] in new_by_id:
                    details_by_invoice[detail["invoice_id"]].append(detail)
            numeric_details = {"quantity", "price", "amount", "tax_amount"}
            for invoice_id, record in new_by_id.items():
                actual = after_by_id[invoice_id]
                for field, expected in record["values"].items():
                    if field in ("ocr_result", "invoice_date", "total_amount", "tax_amount"):
                        continue
                    if actual[field] != expected:
                        raise RuntimeError(f"票号 {record['invoice_number']} 的 {field} 核对失败，已回滚")
                if actual["invoice_date"] != date.fromisoformat(record["values"]["invoice_date"]):
                    raise RuntimeError("开票日期核对失败，已回滚")
                for field in ("total_amount", "tax_amount"):
                    if actual[field] != Decimal(record["values"][field]):
                        raise RuntimeError("票面金额核对失败，已回滚")
                metadata = json.loads(actual["ocr_result"])
                original_metadata = json.loads(record["values"]["ocr_result"])
                for field, value in original_metadata["tax_excel"].items():
                    if metadata["tax_excel"].get(field) != value:
                        raise RuntimeError("导入来源或红冲状态核对失败，已回滚")
                actual_details = details_by_invoice[invoice_id]
                if len(actual_details) != len(record["details"]):
                    raise RuntimeError("发票商品明细数量核对失败，已回滚")
                for actual_detail, expected_detail in zip(actual_details, record["details"]):
                    for field, expected in expected_detail.items():
                        if field in numeric_details and expected is not None:
                            expected = Decimal(expected)
                        if actual_detail[field] != expected:
                            raise RuntimeError("发票商品明细内容核对失败，已回滚")
            report.update(imported=len(new), final_count=len(after_invoices),
                          existing_preserved=True, payment_links_preserved=True,
                          verified=True, new_invoice_ids=list(new_by_id))
            # Write the verification receipt before the database commit; it is
            # explicitly labelled uncommitted until commit exits successfully.
            write_json(audit_dir / "verified-before-commit.json", report)
        report["committed"] = True
        write_json(audit_dir / "result.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description="正式发票库税务 Excel 导入（默认仅预览）")
    parser.add_argument("--import", dest="commit", action="store_true", help="查重、备份、导入并核对")
    parser.add_argument("--preview", action="store_true", help="仅查重并显示预计导入数量")
    parser.add_argument("--payload", type=Path, default=DEFAULT_PAYLOAD, help="加密数据包路径")
    parser.add_argument("--key-file", type=Path, help="仓库外的解密密钥文件；默认交互输入")
    args = parser.parse_args()
    if args.commit and args.preview:
        parser.error("请选择 --preview 或 --import")
    payload = load_payload(args.payload, args.key_file)
    project_root = Path.cwd()
    if not (project_root / "pear_admin").is_dir():
        raise SystemExit("请从现有 web 容器的 /app 项目目录执行脚本")
    sys.path.insert(0, str(project_root))
    from flask import Flask
    from configs import config
    from pear_admin.extensions import db
    from pear_admin.orms import MaterialInvoiceORM, MaterialInvoiceDetailORM
    from pear_admin.orms.pay import pay_invoice_relation
    app = Flask("invoice-tax-one-off-import")
    app.config.from_object(config["prod"])
    db.init_app(app)
    # Deliberately initialize only the database, without OSS/OCR/scheduler jobs.
    with app.app_context():
        result = run_import(db.engine, MaterialInvoiceORM.__table__, MaterialInvoiceDetailORM.__table__,
                            pay_invoice_relation, payload,
                            project_root / "instance" / "invoice-tax-import-20261004" / "audit",
                            commit=args.commit)
        print(json.dumps({k: v for k, v in result.items() if k != "new_invoice_ids"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print("导入未完成：" + str(exc), file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:
        print("导入未完成，请检查数据库连接及部署环境（" + type(exc).__name__ + "）。", file=sys.stderr)
        raise SystemExit(1)
