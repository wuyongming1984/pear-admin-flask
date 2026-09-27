"""Seed clearly marked, synthetic invoices in the local SQLite database only."""
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import sqlite3


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / 'instance' / 'pear_admin.db'
PREFIX = 'LOCAL-TEST-INVOICE-20260928-'
MARKER = '本地发票测试数据 20260928；全部为虚构样例，不可报销、抵扣或作为真实凭证。'


def insert(connection, table, values):
    columns = ','.join(values)
    placeholders = ','.join('?' for _ in values)
    return connection.execute(
        f'INSERT INTO {table} ({columns}) VALUES ({placeholders})',
        tuple(values.values()),
    ).lastrowid


def money(value):
    return str(Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def main():
    if not DATABASE.is_file():
        raise SystemExit('Local database is missing; no database was created.')
    now = datetime.now()
    stamp = now.strftime('%Y%m%d-%H%M%S-%f')
    backup = DATABASE.with_name(f'pear_admin.before-invoice-test-{stamp}.db')
    connection = sqlite3.connect(DATABASE, timeout=30)
    connection.execute('PRAGMA foreign_keys=ON')
    with sqlite3.connect(backup) as target:
        connection.backup(target)
    before = connection.execute('SELECT COUNT(*) FROM material_invoice').fetchone()[0]
    existing_fk_findings = connection.execute('PRAGMA foreign_key_check').fetchall()
    timestamp = now.isoformat(sep=' ', timespec='seconds')
    variants = [
        ('材料采购', '测试建材供应公司', '13', [('镀锌钢管', 'DN50', '米', '120', '38.50'), ('管件', 'DN50', '套', '24', '16.80')]),
        ('苗木采购', '测试园林苗木公司', '0', [('香樟', '胸径12cm', '株', '12', '850'), ('麦冬', '营养钵', '盆', '600', '1.25')]),
        ('施工劳务', '测试园林施工公司', '9', [('绿化种植服务', '人工', '工日', '18', '350'), ('养护服务', '人工', '工日', '6', '280')]),
        ('机械租赁', '测试机械租赁公司', '13', [('小型挖掘机租赁', '3.5t', '台班', '8', '1200'), ('运输车辆租赁', '5t', '台班', '4', '680')]),
        ('技术服务', '测试工程技术公司', '6', [('测量服务', '现场测绘', '项', '1', '3500'), ('图纸整理服务', '竣工资料', '项', '1', '1280')]),
        ('办公用品', '测试办公用品公司', '3', [('复印纸', 'A4/80g', '箱', '5', '135.60'), ('档案盒', '55mm', '个', '30', '8.50')]),
    ]
    added, skipped, dictionaries = [], [], []
    with connection:
        for code, title, entries in [
            ('fpdl', '发票大类', [(f'TEST_CAT_{i+1}', variant[0]) for i, variant in enumerate(variants)]),
            ('kfdk', '可否抵扣', [('TEST_YES', '可抵扣（测试）'), ('TEST_NO', '不可抵扣（测试）')]),
        ]:
            found = connection.execute('SELECT id FROM base_dic WHERE code=?', (code,)).fetchone()
            if found:
                dic_id = found[0]
            else:
                dic_id = insert(connection, 'base_dic', dict(code=code, name=title, valid_mark='Y', create_time=timestamp, update_time=timestamp))
                dictionaries.append(dic_id)
            for order, (entry_code, label) in enumerate(entries, 1):
                exists = connection.execute('SELECT id FROM base_dic_detail WHERE dic_id=? AND code=?', (dic_id, entry_code)).fetchone()
                if not exists:
                    insert(connection, 'base_dic_detail', dict(dic_id=dic_id, code=entry_code, value=label if code == 'kfdk' else label+'（测试）', order_no=order, valid_mark='Y', create_time=timestamp, update_time=timestamp))

        for index in range(24):
            number = PREFIX + f'{index+1:03d}'
            if connection.execute('SELECT 1 FROM material_invoice WHERE invoice_number=?', (number,)).fetchone():
                skipped.append(number)
                continue
            category, seller, rate, goods = variants[index % len(variants)]
            status = 'pending' if index in (20, 21) else 'failed' if index in (22, 23) else 'completed'
            details = []
            if status == 'completed':
                for name, spec, unit, quantity, price in goods:
                    quantity = Decimal(quantity) + index // len(variants)
                    amount = Decimal(money(quantity * Decimal(price)))
                    tax = money(amount * Decimal(rate) / 100)
                    details.append(dict(name=name+'（测试）', spec=spec, unit=unit, quantity=str(quantity), price=price, amount=str(amount), tax_rate='免税' if rate == '0' else rate+'%', tax_amount=tax, create_at=timestamp))
            net = sum((Decimal(item['amount']) for item in details), Decimal(0))
            tax_total = sum((Decimal(item['tax_amount']) for item in details), Decimal(0))
            invoice_id = insert(connection, 'material_invoice', dict(
                invoice_number=number, invoice_code='TEST-ONLY',
                invoice_date=(date(2026, 9, 28)-timedelta(days=index)).isoformat(),
                buyer_name=f'【测试】园林项目公司{index % 3 + 1}', buyer_tax_num=f'TEST-BUYER-{index % 3 + 1:03d}',
                seller_name='【测试】'+seller, seller_tax_num=f'TEST-SELLER-{index % 6 + 1:03d}',
                buyer_address_phone='测试地址；电话未设置', seller_address_phone='测试地址；电话未设置',
                buyer_bank_account='测试银行；无真实银行账号', seller_bank_account='测试银行；无真实银行账号',
                invoice_type='普通发票' if rate in ('0', '3') else '增值税专用发票',
                invoice_name='【测试样例】'+('普通发票' if rate in ('0', '3') else '增值税专用发票'),
                tax_rate=rate, total_amount=money(net), tax_amount=money(tax_total),
                details_json=json.dumps([{**item, 'tax': item['tax_amount']} for item in details], ensure_ascii=False),
                remarks=MARKER+f' 类型：{category}；识别状态为模拟数据。',
                payee='测试收款员', checker='测试复核员', drawer='测试开票员',
                invoice_category=f'TEST_CAT_{index % 6 + 1}', deductible='TEST_NO' if rate in ('0', '3') else 'TEST_YES',
                ocr_status=status, ocr_error='模拟识别失败：样例用于界面检查，未调用OCR。' if status == 'failed' else None,
                create_at=timestamp, update_at=timestamp,
            ))
            for detail in details:
                insert(connection, 'material_invoice_detail', dict(invoice_id=invoice_id, **detail))
            added.append(dict(id=invoice_id, invoice_number=number, status=status, total=money(net+tax_total), lines=len(details)))
        # Existing root-menu/department parent IDs may reference the sentinel 0.
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == existing_fk_findings
        assert connection.execute('SELECT COUNT(*) FROM material_invoice').fetchone()[0] == before + len(added)
        assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    result = dict(database=str(DATABASE), backup=str(backup), before=before, added=added, skipped=skipped, created_dictionary_ids=dictionaries)
    manifest = ROOT / 'instance' / f'invoice-test-seed-{stamp}.json'
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(added=len(added), skipped=len(skipped), before=before, after=before+len(added), backup=str(backup), manifest=str(manifest)), ensure_ascii=False))
    connection.close()


if __name__ == '__main__':
    main()
