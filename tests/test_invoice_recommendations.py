"""Smart recommendations use isolated data and never persist user selections."""
import unittest
from datetime import date, datetime

from sqlalchemy import event
from sqlalchemy import text

from tests import test_mobile_api
from pear_admin.extensions import db
from pear_admin.orms import MaterialInvoiceORM, OrderORM, PayORM, PayerORM, ProjectORM, SupplierORM
from pear_admin.orms.pay import pay_invoice_relation


class InvoiceRecommendationsTest(unittest.TestCase):
    setUp = test_mobile_api.MobileAPITest.setUp
    tearDown = test_mobile_api.MobileAPITest.tearDown
    url = '/api/v1/invoice-links/payments/recommendations'

    def seed(self):
        self.supplier = SupplierORM(type_id=1, name='杭州雅鸿装饰工程有限公司（钱顺怡）',
            contact_person='钱顺怡', phone='', bank_name='', account_number='')
        self.payer = PayerORM(type_id=1, name='杭州园林建设有限公司')
        self.project = ProjectORM(project_name='项目甲')
        self.other_project = ProjectORM(project_name='项目乙')
        db.session.add_all([self.supplier, self.payer, self.project, self.other_project])
        db.session.flush()
        self.order = OrderORM(order_number='ORDER-1', material_name='材料', project_id=self.project.id,
            supplier_id=self.supplier.id, supplier_contact_person='钱顺怡')
        db.session.add(self.order)
        db.session.flush()
        self.pay = self.payment('PAY-1', '113.00')
        self.exact = self.invoice('EXACT', '100.00', '13.00')
        self.first = self.invoice('PART-A', '40.00', '5.20')
        self.second = self.invoice('PART-B', '60.00', '7.80')
        db.session.commit()

    def invoice(self, number, net, tax='0.00', **changes):
        data = dict(invoice_number=number, seller_name='杭州雅鸿装饰工程有限公司',
            buyer_name=self.payer.name, invoice_date=date(2026, 10, 1),
            total_amount=net, tax_amount=tax, project_id=self.project.id)
        data.update(changes)
        invoice = MaterialInvoiceORM(**data)
        db.session.add(invoice)
        db.session.flush()
        return invoice

    def payment(self, number, amount, **changes):
        data = dict(pay_number=number, current_payment_amount=amount, order_id=self.order.id,
            payee_supplier_id=self.supplier.id, payer_supplier_id=self.payer.id,
            create_at=datetime(2026, 10, 4))
        data.update(changes)
        payment = PayORM(**data)
        db.session.add(payment)
        db.session.flush()
        return payment

    def recommend(self, **changes):
        data = dict(pay_id=self.pay.id, payee_supplier_id=self.supplier.id,
            payer_supplier_id=self.payer.id, order_id=self.order.id,
            current_payment_amount='113.00', create_at='2026-10-04 10:00:00',
            selected_invoice_ids=[])
        data.update(changes)
        response = self.client.post(self.url, json=data, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.json)
        self.assertEqual(response.json['code'], 0, response.json)
        return response.json['data']

    def test_invoice_gross_amount_and_exact_single_or_multiple_matches(self):
        self.seed()
        data = self.recommend()
        self.assertEqual(data['context'], dict(target_amount='113.00', amount_basis='current_payment_amount',
            selected_gross='0.00', remaining='113.00'))
        self.assertEqual(data['candidates'][0]['id'], self.exact.id)
        self.assertEqual(data['candidates'][0]['gross_amount'], '113.00')
        groups = {tuple(sorted(c['invoice_ids'])) for c in data['combinations'] if c['difference'] == '0.00'}
        self.assertIn((self.exact.id,), groups)
        self.assertIn(tuple(sorted([self.first.id, self.second.id])), groups)

    def test_positive_invoice_amount_has_priority_and_nonpositive_falls_back(self):
        self.seed()
        data = self.recommend(invoice_amount='45.20')
        self.assertEqual(data['context']['amount_basis'], 'invoice_amount')
        self.assertEqual(data['context']['target_amount'], '45.20')
        self.assertEqual(data['candidates'][0]['id'], self.first.id)
        for value in ('0.00', '-1.00', None, ''):
            data = self.recommend(invoice_amount=value)
            self.assertEqual(data['context']['target_amount'], '113.00')

    def test_no_exact_combination_does_not_offer_approximate_amounts(self):
        self.seed()
        data = self.recommend(invoice_amount='115.00')
        self.assertTrue(data['candidates'])
        self.assertEqual(data['combinations'], [])

    def test_missing_positive_target_with_negative_selected_invoice_does_not_recommend(self):
        self.seed()
        red = self.invoice('SELECTED-RED', '-100.00', '-13.00')
        db.session.commit()
        data = self.recommend(current_payment_amount=None, selected_invoice_ids=[red.id])
        self.assertEqual(data['context']['target_amount'], '0.00')
        self.assertEqual(data['combinations'], [])

    def test_unrelated_invoice_amounts_are_not_loaded_before_supplier_filter(self):
        self.seed()
        unrelated = self.invoice('OLD-UNRELATED', '10.00', seller_name='上海其他材料有限公司')
        unrelated_id = unrelated.id
        db.session.execute(text('UPDATE material_invoice SET total_amount = :amount WHERE id = :id'),
            {'amount': 'malformed legacy amount', 'id': unrelated_id})
        db.session.commit()
        try:
            data = self.recommend()
        except TypeError:
            self.fail('无关销售方的旧金额数据不应进入推荐金额读取')
        self.assertNotIn(unrelated_id, [c['id'] for c in data['candidates']])

    def test_selected_invoice_is_locked_and_only_remaining_amount_is_recommended(self):
        self.seed()
        self.pay.invoices.append(self.first)
        db.session.commit()
        data = self.recommend(selected_invoice_ids=[self.first.id])
        self.assertEqual(data['context']['selected_gross'], '45.20')
        self.assertEqual(data['context']['remaining'], '67.80')
        selected = next(c for c in data['candidates'] if c['id'] == self.first.id)
        self.assertTrue(selected['already_selected'])
        self.assertFalse(selected['can_recommend'])
        self.assertEqual(data['combinations'][0]['invoice_ids'], [self.second.id])
        self.assertFalse(any(self.first.id in c['invoice_ids'] for c in data['combinations']))
        self.assertEqual([i.id for i in self.pay.invoices], [self.first.id])

    def test_other_payment_links_cross_project_and_red_invoices_are_manual_candidates(self):
        self.seed()
        other_pay = self.payment('PAY-OTHER', '113.00')
        other_pay.invoices.append(self.exact)
        red = self.invoice('RED', '-100.00', '-13.00')
        red_marked = self.invoice('RED-POSITIVE', '113.00', invoice_type='红字发票')
        cross = self.invoice('CROSS', '113.00', project_id=self.other_project.id)
        db.session.commit()
        data = self.recommend()
        rows = {c['id']: c for c in data['candidates']}
        self.assertEqual(rows[self.exact.id]['linked_payments'], [{'id': other_pay.id, 'pay_number': 'PAY-OTHER'}])
        blocked = [self.exact.id, red.id, red_marked.id, cross.id]
        for iid in blocked:
            self.assertFalse(rows[iid]['can_recommend'])
            self.assertTrue(rows[iid]['reasons'])
        self.assertFalse(any(set(blocked) & set(c['invoice_ids']) for c in data['combinations']))

    def test_missing_amount_or_dates_keeps_candidates_without_claiming_an_exact_match(self):
        self.seed()
        self.exact.invoice_date = None
        self.first.buyer_name = None
        db.session.commit()
        data = self.recommend(current_payment_amount=None, invoice_amount=None, create_at=None,
            payer_supplier_id=None, order_id=None)
        self.assertEqual(data['context']['target_amount'], '0.00')
        self.assertEqual(data['combinations'], [])
        self.assertEqual(len(data['candidates']), 3)

    def test_missing_invoice_net_or_tax_is_unknown_and_never_automatically_recommended(self):
        self.seed()
        cases = [('MISSING-NET', None, '13.00'), ('MISSING-TAX', '100.00', None),
            ('MISSING-BOTH', None, None)]
        missing = []
        for number, net, tax in cases:
            invoice = self.invoice(number, '100.00', '13.00')
            missing.append((invoice.id, net, tax))
            db.session.execute(db.update(MaterialInvoiceORM).where(MaterialInvoiceORM.id == invoice.id)
                .values(total_amount=net, tax_amount=tax))
        zero_tax = self.invoice('CONFIRMED-ZERO-TAX', '113.00', '0.00')
        zero_tax_id = zero_tax.id
        db.session.commit()
        data = self.recommend()
        rows = {row['id']: row for row in data['candidates']}
        for iid, net, tax in missing:
            row = rows[iid]
            self.assertEqual(row['total_amount'], net)
            self.assertEqual(row['tax_amount'], tax)
            self.assertIsNone(row['gross_amount'])
            self.assertIsNone(row['amount_difference'])
            self.assertFalse(row['can_recommend'])
            self.assertTrue(any('待核实' in reason for reason in row['reasons']))
        self.assertEqual(rows[zero_tax_id]['gross_amount'], '113.00')
        self.assertTrue(rows[zero_tax_id]['can_recommend'])
        self.assertFalse(any({iid for iid, _, _ in missing} & set(group['invoice_ids'])
            for group in data['combinations']))

    def test_selected_invoice_with_missing_tax_makes_total_and_remaining_unknown(self):
        self.seed()
        missing_id, known_id = self.exact.id, self.first.id
        db.session.execute(db.update(MaterialInvoiceORM).where(MaterialInvoiceORM.id == missing_id)
            .values(tax_amount=None))
        db.session.commit()
        data = self.recommend(selected_invoice_ids=[missing_id, known_id])
        self.assertEqual(data['context']['target_amount'], '113.00')
        self.assertIsNone(data['context']['selected_gross'])
        self.assertIsNone(data['context']['remaining'])
        self.assertTrue(any('待核实' in reason for reason in data['context']['reasons']))
        self.assertEqual(data['combinations'], [])
        self.assertTrue(all(not row['can_recommend'] for row in data['candidates']))
        self.assertTrue(all(row['amount_difference'] is None for row in data['candidates']))
        self.assertTrue({missing_id, known_id} <= {row['id'] for row in data['candidates'] if row['already_selected']})

    def test_unrelated_sellers_are_excluded_but_selected_ones_are_preserved(self):
        self.seed()
        unrelated = self.invoice('UNRELATED', '113.00', seller_name='上海其他材料有限公司')
        db.session.commit()
        self.assertNotIn(unrelated.id, [c['id'] for c in self.recommend()['candidates']])
        data = self.recommend(selected_invoice_ids=[unrelated.id])
        row = next(c for c in data['candidates'] if c['id'] == unrelated.id)
        self.assertTrue(row['already_selected'])
        self.assertFalse(row['can_recommend'])
        self.assertEqual(data['context']['selected_gross'], '113.00')

    def test_invalid_ids_amounts_and_dates_are_rejected_without_mutation(self):
        self.seed()
        base = dict(payee_supplier_id=self.supplier.id, current_payment_amount='113.00')
        invalid = [dict(payee_supplier_id=v) for v in (None, '', True, 0, -1, '1.2', 99999)]
        invalid += [dict(current_payment_amount=v) for v in (True, 'not-money', 'NaN', 'Infinity', '1.001', '10000000000000000.00')]
        invalid += [dict(invoice_amount='NaN'), dict(pay_id=True), dict(pay_id=99999),
            dict(payer_supplier_id='bad'), dict(payer_supplier_id=99999), dict(order_id=99999),
            dict(create_at='yesterday'), dict(selected_invoice_ids=[True]), dict(selected_invoice_ids=[99999]),
            dict(selected_invoice_ids='bad')]
        for values in invalid:
            with self.subTest(values=values):
                response = self.client.post(self.url, json={**base, **values}, headers=self.headers)
                self.assertEqual(response.status_code, 400, response.json)
                self.assertNotEqual(response.json['code'], 0)
        self.assertEqual(db.session.execute(db.select(pay_invoice_relation)).all(), [])

    def test_requires_login_and_does_not_save_recommendations(self):
        self.seed()
        self.assertIn(self.client.post(self.url, json={}).status_code, (401, 403))
        self.recommend()
        self.assertEqual(db.session.execute(db.select(pay_invoice_relation)).all(), [])
        self.assertEqual(db.session.get(PayORM, self.pay.id).updated_at, None)

    def test_candidate_result_is_truncated_and_combination_search_is_bounded(self):
        self.seed()
        for i in range(205):
            self.invoice(f'MANY-{i}', '10.00')
        db.session.commit()
        data = self.recommend()
        self.assertEqual(data['total_count'], 208)
        self.assertTrue(data['truncated'])
        self.assertEqual(len(data['candidates']), 200)
        self.assertEqual(data['combination_limit'], 30)
        self.assertLessEqual(len(data['combinations']), 5)
        self.assertTrue(all(1 <= len(c['invoice_ids']) <= 3 for c in data['combinations']))

    def test_two_hundred_selected_invoices_do_not_hide_a_new_exact_candidate(self):
        self.seed()
        selected = [self.invoice(f'SELECTED-{i}', '0.01').id for i in range(200)]
        exact = self.invoice('NEW-EXACT', '1.00')
        db.session.commit()
        data = self.recommend(invoice_amount='3.00', selected_invoice_ids=selected)
        ids = {c['id'] for c in data['candidates']}
        self.assertTrue(set(selected) <= ids)
        self.assertIn(exact.id, ids)
        self.assertEqual(data['context']['remaining'], '1.00')
        self.assertEqual(data['combinations'][0]['invoice_ids'], [exact.id])
        self.assertTrue(all(set(c['invoice_ids']) <= ids for c in data['combinations']))
        self.assertFalse(data['truncated'])

    def test_recommendation_queries_are_lightweight_and_do_not_grow_per_invoice(self):
        self.seed()
        for i in range(15):
            self.invoice(f'LIGHT-{i}', '10.00', ocr_result='large private OCR')
        db.session.commit()
        sid, pid, oid = self.supplier.id, self.payer.id, self.order.id
        db.session.remove()
        queries = []
        def track(conn, cursor, statement, parameters, context, executemany):
            queries.append(statement)
        event.listen(db.engine, 'before_cursor_execute', track)
        try:
            response = self.client.post(self.url, json=dict(payee_supplier_id=sid, payer_supplier_id=pid,
                order_id=oid, current_payment_amount='113.00'), headers=self.headers)
        finally:
            event.remove(db.engine, 'before_cursor_execute', track)
        self.assertEqual(response.status_code, 200, response.json)
        self.assertLessEqual(len(queries), 8, queries)
        self.assertFalse(any('ocr_result' in q or 'material_invoice_detail' in q for q in queries), queries)
        self.assertTrue(all(q.lstrip().upper().startswith('SELECT') for q in queries), queries)

    def test_reverse_invoice_recommendations_use_gross_and_multiple_payments(self):
        self.seed()
        first = self.payment('SPLIT-A', '45.20')
        second = self.payment('SPLIT-B', '67.80')
        db.session.commit()
        response = self.client.get(f'/api/v1/invoice-links/invoices/{self.exact.id}/payments', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json['data']
        self.assertIn('context', data)
        self.assertEqual(data['context'], dict(target_amount='113.00', amount_basis='invoice_gross',
            selected_gross='0.00', remaining='113.00'))
        self.assertEqual(data['matched'][0]['id'], self.pay.id)
        groups = {tuple(sorted(c['payment_ids'])) for c in data['combinations'] if c['difference'] == '0.00'}
        self.assertIn((self.pay.id,), groups)
        self.assertIn(tuple(sorted([first.id, second.id])), groups)

    def test_reverse_invoice_missing_net_or_tax_keeps_target_unknown(self):
        self.seed()
        invoice_id = self.exact.id
        for net, tax in [(None, '13.00'), ('100.00', None), (None, None)]:
            with self.subTest(net=net, tax=tax):
                db.session.execute(db.update(MaterialInvoiceORM).where(MaterialInvoiceORM.id == invoice_id)
                    .values(total_amount=net, tax_amount=tax))
                db.session.commit()
                data = self.client.get(f'/api/v1/invoice-links/invoices/{invoice_id}/payments', headers=self.headers).json['data']
                self.assertIsNone(data['context']['target_amount'])
                self.assertIsNone(data['context']['remaining'])
                self.assertEqual(data['context']['selected_gross'], '0.00')
                self.assertTrue(any('待核实' in reason for reason in data['context']['reasons']))
                self.assertEqual(data['combinations'], [])
                self.assertTrue(data['matched'])
                self.assertTrue(all(not row['can_recommend'] for row in data['matched']))
                self.assertTrue(all(row['amount_difference'] is None for row in data['matched']))

    def test_reverse_linked_payment_with_missing_amount_keeps_selected_total_unknown(self):
        self.seed()
        locked = self.payment('MISSING-PAYMENT', None)
        locked_id = locked.id
        self.exact.related_pays.append(locked)
        db.session.commit()
        data = self.client.get(f'/api/v1/invoice-links/invoices/{self.exact.id}/payments', headers=self.headers).json['data']
        self.assertEqual(data['context']['target_amount'], '113.00')
        self.assertIsNone(data['context']['selected_gross'])
        self.assertIsNone(data['context']['remaining'])
        self.assertTrue(any('待核实' in reason for reason in data['context']['reasons']))
        self.assertEqual(data['combinations'], [])
        linked = next(row for row in data['linked'] if row['id'] == locked_id)
        self.assertIsNone(linked['current_payment_amount'])
        self.assertTrue(all(not row['can_recommend'] for row in data['matched']))

    def test_reverse_unlinked_payment_with_missing_amount_remains_a_manual_candidate(self):
        self.seed()
        missing = self.payment('MISSING-UNLINKED-PAYMENT', None)
        missing_id = missing.id
        db.session.commit()
        data = self.client.get(f'/api/v1/invoice-links/invoices/{self.exact.id}/payments', headers=self.headers).json['data']
        row = next(item for item in data['matched'] if item['id'] == missing_id)
        self.assertIsNone(row['current_payment_amount'])
        self.assertIsNone(row['amount_difference'])
        self.assertFalse(row['can_recommend'])
        self.assertTrue(any('待核实' in reason for reason in row['reasons']))
        self.assertTrue(all(missing_id not in group['payment_ids'] for group in data['combinations']))

    def test_reverse_protects_existing_links_other_invoices_and_cross_project(self):
        self.seed()
        locked = self.payment('LOCKED', '45.20')
        self.exact.related_pays.append(locked)
        self.pay.invoices.append(self.second)
        other_order = OrderORM(order_number='OTHER-ORDER', material_name='材料', project_id=self.other_project.id)
        db.session.add(other_order)
        db.session.flush()
        cross = self.payment('CROSS-PAY', '67.80', order_id=other_order.id)
        negative = self.payment('NEGATIVE', '-67.80')
        remaining = self.payment('REMAINING', '67.80')
        db.session.commit()
        data = self.client.get(f'/api/v1/invoice-links/invoices/{self.exact.id}/payments', headers=self.headers).json['data']
        self.assertIn('context', data)
        self.assertEqual(data['context']['selected_gross'], '45.20')
        self.assertEqual(data['context']['remaining'], '67.80')
        rows = {r['id']: r for r in data['matched']}
        for pid in [locked.id, self.pay.id, cross.id, negative.id]:
            self.assertFalse(rows[pid]['can_recommend'])
        self.assertEqual(data['combinations'][0]['payment_ids'], [remaining.id])
        self.assertEqual([p['id'] for p in data['linked']], [locked.id])

    def test_reverse_two_hundred_linked_payments_do_not_hide_a_new_exact_candidate(self):
        self.seed()
        selected = [self.payment(f'LINKED-{i}', '0.01') for i in range(200)]
        self.exact.related_pays.extend(selected)
        exact = self.payment('NEW-EXACT-PAY', '111.00')
        db.session.commit()
        data = self.client.get(f'/api/v1/invoice-links/invoices/{self.exact.id}/payments', headers=self.headers).json['data']
        ids = {c['id'] for c in data['matched']}
        self.assertEqual(len(data['linked']), 200)
        self.assertIn(exact.id, ids)
        self.assertEqual(data['context']['remaining'], '111.00')
        self.assertEqual(data['combinations'][0]['payment_ids'], [exact.id])
        self.assertTrue(all(set(c['payment_ids']) <= ids for c in data['combinations']))
        self.assertFalse(data['truncated'])


if __name__ == '__main__':
    unittest.main()
