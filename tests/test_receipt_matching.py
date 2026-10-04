"""Smart receipt candidates are ranked globally and never create links."""
import unittest
from datetime import date, datetime
from decimal import Decimal

from pear_admin.extensions import db
from pear_admin.orms import PayORM, PaymentReceiptORM, PayerORM, SupplierORM
from pear_admin.orms.payment_receipt import pay_receipt_relation
from tests import test_mobile_api


class ReceiptMatchingTest(unittest.TestCase):
    setUp = test_mobile_api.MobileAPITest.setUp
    tearDown = test_mobile_api.MobileAPITest.tearDown
    base = '/api/v1/payment-receipts'
    match_keys = ('match_score', 'match_level', 'match_reasons', 'match_conflicts', 'recommended')

    def pay(self, payee='测试园林有限公司', payer='付款建设有限公司', amount='120.50', **extra):
        supplier = SupplierORM(type_id=1, name=payee, contact_person='', phone='', bank_name='', account_number='') if payee else None
        payer_row = PayerORM(type_id=1, name=payer) if payer else None
        db.session.add_all([row for row in (supplier, payer_row) if row])
        db.session.flush()
        values = dict(pay_number=f'PAY-{db.session.query(PayORM).count() + 1}',
                      payee_supplier_id=supplier.id if supplier else None,
                      payer_supplier_id=payer_row.id if payer_row else None,
                      current_payment_amount=amount, create_at=datetime(2024, 1, 1))
        values.update(extra)
        row = PayORM(**values)
        db.session.add(row)
        db.session.commit()
        return row

    def receipt(self, payee='测试园林有限公司', payer='付款建设有限公司', amount='120.50', **extra):
        number = db.session.query(PaymentReceiptORM).count() + 1
        values = dict(receipt_number=f'BANK-{number:03}', payee_name=payee, payer_name=payer,
                      amount=amount, file_name=f'回单-{number}.pdf', file_path=f'/uploads/receipt-{number}.pdf',
                      file_type='pdf', file_size=10, file_hash=f'{number:064x}')
        values.update(extra)
        row = PaymentReceiptORM(**values)
        db.session.add(row)
        db.session.commit()
        return row

    def for_pay(self, pay, **args):
        response = self.client.get(f'{self.base}/for-payment/{pay.id}', headers=self.headers,
                                   query_string={'mode': 'smart', **args})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['code'], 0)
        return response.json['data']

    def for_receipt(self, receipt, **args):
        response = self.client.get(f'{self.base}/{receipt.id}/payments', headers=self.headers,
                                   query_string={'mode': 'smart', **args})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['code'], 0)
        return response.json['data']

    def test_payment_smart_ranks_an_old_exact_match_before_paginating(self):
        pay = self.pay()
        best = self.receipt()
        later = [self.receipt(amount='999.00') for _ in range(24)]
        data = self.for_pay(pay)
        self.assertEqual(data['candidates'][0]['id'], best.id)
        self.assertEqual(data['count'], 25)
        self.assertEqual(len(data['candidates']), 20)
        self.assertEqual(data['candidates'][0].get('match_level'), 'high')
        page2 = self.for_pay(pay, page=2)
        self.assertEqual(len(page2['candidates']), 5)
        self.assertEqual({row['id'] for row in data['candidates'] + page2['candidates']}, {best.id, *(row.id for row in later)})

    def test_reverse_smart_ranks_an_old_payment_before_paginating(self):
        receipt = self.receipt()
        best = self.pay()
        for _ in range(21):
            self.pay(amount='999.00')
        data = self.for_receipt(receipt)
        self.assertEqual(data['candidates'][0]['id'], best.id)
        self.assertEqual(data['count'], 22)
        self.assertEqual(len(data['candidates']), 20)

    def test_same_amount_with_wrong_company_is_a_conflicted_low_candidate(self):
        receipt = self.receipt()
        wrong = self.pay(payee='无关建筑有限公司')
        candidate = self.for_receipt(receipt)['candidates'][0]
        self.assertEqual(candidate['id'], wrong.id)
        self.assertEqual(candidate.get('match_level'), 'low')
        self.assertFalse(candidate['recommended'])
        self.assertTrue(any('收款' in reason for reason in candidate.get('match_conflicts', [])))
        self.assertTrue(any('金额' in reason for reason in candidate.get('match_reasons', [])))

    def test_wrong_payer_downgrades_matching_payee_and_amount(self):
        receipt = self.receipt()
        self.pay(payer='无关建设有限公司')
        candidate = self.for_receipt(receipt)['candidates'][0]
        self.assertEqual(candidate.get('match_level'), 'low')
        self.assertFalse(candidate['recommended'])
        self.assertTrue(any('付款' in reason for reason in candidate.get('match_conflicts', [])))

    def test_payer_and_nearby_date_cannot_override_both_payee_and_amount_conflicts(self):
        receipt = self.receipt(payment_date=date(2026, 10, 4))
        pay = self.pay(payee='无关建筑有限公司', amount='999.00', create_at=datetime(2026, 10, 4))
        self.assertEqual(self.for_receipt(receipt)['count'], 0)
        self.assertEqual(self.for_pay(pay)['candidates'], [])

    def test_payer_only_evidence_stays_low_when_main_fields_are_missing(self):
        receipt = self.receipt(payee='', amount=None)
        self.pay(payee='', amount=None)
        data = self.for_receipt(receipt)
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['candidates'][0].get('match_level'), 'low')
        self.assertFalse(data['candidates'][0]['recommended'])
        self.assertIn('收款单位', data.get('match_hint', ''))
        self.assertIn('金额', data.get('match_hint', ''))

    def test_wrong_amount_is_explained_and_never_high(self):
        receipt = self.receipt(amount='120.51')
        self.pay()
        candidate = self.for_receipt(receipt)['candidates'][0]
        self.assertEqual(candidate.get('match_level'), 'low')
        self.assertFalse(candidate['recommended'])
        self.assertTrue(any('金额' in reason and '0.01' in reason for reason in candidate.get('match_conflicts', [])))

    def test_missing_amount_is_not_treated_as_zero(self):
        pay = self.pay(payee='', payer='', amount='0.00')
        missing = self.receipt(payee='', payer='', amount=None)
        zero = self.receipt(payee='', payer='', amount='0.00')
        data = self.for_pay(pay)
        self.assertEqual([row['id'] for row in data['candidates']], [zero.id])
        self.assertEqual(data['count'], 1)
        self.assertNotIn(missing.id, [row['id'] for row in data['candidates']])
        self.assertEqual(data['candidates'][0].get('match_score'), 40)
        hint = self.for_receipt(missing).get('match_hint', '')
        self.assertIn('金额', hint)

    def test_missing_payer_does_not_conflict_or_block_a_strong_match(self):
        pay = self.pay(payer='')
        receipt = self.receipt(payer='')
        candidate = self.for_pay(pay)['candidates'][0]
        self.assertEqual(candidate['id'], receipt.id)
        self.assertEqual(candidate.get('match_level'), 'high')
        self.assertEqual(candidate.get('match_score'), 75)
        self.assertEqual(candidate.get('match_conflicts'), [])
        self.assertIn('付款', self.for_receipt(receipt).get('match_hint', ''))

    def test_fuzzy_name_match_has_lower_score_than_normalized_exact_name(self):
        pay = self.pay()
        exact = self.receipt(payee=' 测试 园林有限公司 ')
        fuzzy = self.receipt(payee='测试园林')
        candidates = self.for_pay(pay)['candidates']
        self.assertEqual([row['id'] for row in candidates], [exact.id, fuzzy.id])
        self.assertEqual([row.get('match_score') for row in candidates], [95, 85])

    def test_nearby_date_is_only_auxiliary_and_cannot_create_a_candidate(self):
        receipt = self.receipt(payment_date=date(2026, 10, 4))
        near = self.pay(create_at=datetime(2026, 10, 11))
        far = self.pay(create_at=datetime(2026, 10, 12))
        date_only = self.pay(payee='', payer='', amount=None, create_at=datetime(2026, 10, 4))
        data = self.for_receipt(receipt)
        self.assertEqual([row['id'] for row in data['candidates']], [near.id, far.id])
        self.assertNotIn(date_only.id, [row['id'] for row in data['candidates']])
        self.assertEqual([row.get('match_score') for row in data['candidates']], [100, 95])
        self.assertTrue(any('付款单日期' in reason and '辅助' in reason for reason in data['candidates'][0].get('match_reasons', [])))

    def test_ambiguous_equal_matches_remain_separate_and_get_never_links(self):
        receipt = self.receipt()
        first, second = self.pay(), self.pay()
        before = [{column.key: getattr(pay, column.key) for column in PayORM.__table__.columns} for pay in (first, second)]
        data = self.for_receipt(receipt)
        self.assertEqual({row['id'] for row in data['candidates']}, {first.id, second.id})
        self.assertEqual([row.get('match_level') for row in data['candidates']], ['high', 'high'])
        self.assertEqual(list(db.session.execute(db.select(pay_receipt_relation))), [])
        db.session.expire_all()
        self.assertEqual([{column.key: getattr(pay, column.key) for column in PayORM.__table__.columns} for pay in (first, second)], before)

    def test_pair_has_identical_evidence_in_both_entry_points(self):
        pay = self.pay(create_at=datetime(2026, 10, 2))
        receipt = self.receipt(payment_date=date(2026, 10, 4))
        forward = self.for_pay(pay)['candidates'][0]
        reverse = self.for_receipt(receipt)['candidates'][0]
        self.assertTrue(all(key in forward and key in reverse for key in self.match_keys))
        self.assertEqual({key: forward[key] for key in self.match_keys}, {key: reverse[key] for key in self.match_keys})

    def test_smart_search_excludes_current_links_but_preserves_shared_receipts(self):
        pay, other = self.pay(), self.pay()
        linked, shared, irrelevant = self.receipt(), self.receipt(), self.receipt(payee='另一家公司', payer='', amount=None)
        linked.payments.append(pay)
        shared.payments.append(other)
        db.session.commit()
        data = self.for_pay(pay)
        self.assertEqual([row['id'] for row in data['linked']], [linked.id])
        self.assertEqual([row['id'] for row in data['candidates']], [shared.id])
        self.assertEqual(data['count'], 1)
        self.assertEqual([row['id'] for row in self.for_pay(pay, q=shared.receipt_number)['candidates']], [shared.id])
        self.assertEqual(self.for_pay(pay, q=irrelevant.receipt_number)['count'], 0)
        self.assertEqual(self.for_pay(pay, page=99)['candidates'], [])
        self.assertEqual({row.id for row in shared.payments}, {other.id})

    def test_default_get_and_smart_post_keep_the_original_candidate_contract(self):
        pay = self.pay()
        receipt = self.receipt(amount='999.00')
        endpoint = f'{self.base}/for-payment/{pay.id}'
        data = self.client.get(endpoint, headers=self.headers).json['data']
        self.assertEqual(data['candidates'][0]['id'], receipt.id)
        self.assertTrue(data['candidates'][0]['recommended'])
        self.assertNotIn('match_score', data['candidates'][0])
        data = self.client.post(endpoint + '?mode=smart', headers=self.headers,
                                json={'receipt_ids': []}).json['data']
        self.assertNotIn('match_score', data['candidates'][0])


if __name__ == '__main__':
    unittest.main()
