"""Render-only desktop regressions; no database or application factory."""
from pathlib import Path
import re
import unittest
from html.parser import HTMLParser
from flask import Flask, render_template

class DesktopViewTests(unittest.TestCase):
    def test_component_divs_cannot_close_host_tab(self):
        class DivBalance(HTMLParser):
            depth = 0
            minimum = 0
            def handle_starttag(self, tag, attrs):
                if tag == 'div': self.depth += 1
            def handle_endtag(self, tag):
                if tag == 'div':
                    self.depth -= 1
                    self.minimum = min(self.minimum, self.depth)
        for name in ['project/info/project_info.html', 'supplier/info/supplier_info.html', 'payer/info/payer_info.html', 'order_pay/order_base.html', 'order_pay/pay_base.html']:
            with self.subTest(page=name):
                parser = DivBalance()
                parser.feed((Path(__file__).resolve().parents[1] / 'templates' / name).read_text(encoding='utf-8'))
                self.assertEqual(parser.minimum, 0)
                self.assertEqual(parser.depth, 0)

    def test_order_arrival_input_matches_persisted_field(self):
        from pear_admin.orms.order import OrderORM
        html = (Path(__file__).resolve().parents[1] / 'templates/order_pay/info/order_info.html').read_text(encoding='utf-8')
        field = re.search(r'name="([^"]+)" id="estimated_arrival_time"', html).group(1)
        self.assertIn(field, OrderORM.__table__.columns.keys())
        self.assertEqual(field, 'estimated_arrival_time')

    def test_overview_tabs_have_independent_dom_ids(self):
        app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / 'templates'))
        groups = []
        with app.app_context():
            for page in ['dashboard', 'console', 'analysis']:
                html = render_template('view/' + page + '/index.html')
                ids = re.findall(r'\bid="([^"]+)"', html)
                self.assertEqual(len(ids), len(set(ids)))
                self.assertTrue(any(value.endswith('-chart-status') for value in ids))
                self.assertIn('/api/v1/dashboard/overview', html)
                groups.append(set(ids))
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                self.assertFalse(groups[i] & groups[j])
