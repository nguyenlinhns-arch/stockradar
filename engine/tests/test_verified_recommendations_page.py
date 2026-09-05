import json
from pathlib import Path
import tempfile
import unittest

from scripts.render_verified_recommendations_page import build_content, render_page
from scripts.verify_commercial_density_v1 import visible_main


ROOT = Path(__file__).resolve().parents[2]


class VerifiedRecommendationPageTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'website/public/data/recommendation-history.json').read_text(encoding='utf-8'))

    def test_verified_rows_and_dated_prices_exist_without_javascript(self):
        content = build_content(self.data)
        self.assertLess(content.index('data-ticker="VHM"'), content.index('data-ticker="DCM"'))
        self.assertEqual(content.count('<tr data-verified-row'), 2)
        self.assertEqual(content.count('data-verified-event'), 3)
        for value in ['75.400đ', '75.200đ', '-0,27%', '32.200đ', '32.550đ', '+1,09%', '04/09/2026']:
            self.assertIn(value, content)
        self.assertIn('data-verified-controls disabled', content)
        # The shared Radar runtime treats data-status as a text output target.
        self.assertNotIn(' data-status=', content)
        self.assertIn('chưa chốt', content)
        self.assertNotIn('evidence_sha256', content)

    def test_dcm_update_keeps_original_recommendation_price(self):
        self.data['items'][0]['timeline'][1]['buy_zone'] = [99900, 100000]
        content = build_content(self.data)
        table = content.split('</table>')[0]
        self.assertIn('32.200đ', table)
        self.assertNotIn('99.900đ', table)
        self.assertIn('99.900đ', content)

    def test_unknown_status_does_not_invent_a_sale(self):
        self.data['items'][0]['status'] = 'UNKNOWN'
        with self.assertRaises(ValueError):
            build_content(self.data)

    def test_archived_email_note_is_escaped(self):
        self.data['items'][0]['timeline'][0]['note'] = '<img src=x onerror="alert(1)">'
        content = build_content(self.data)
        self.assertNotIn('<img', content)
        self.assertIn('&lt;img', content)

    def test_missing_prices_are_not_zero_returns(self):
        self.data['items'][0].update(latest_price=None, price_change_pct=None, price_date=None)
        content = build_content(self.data)
        self.assertIn('<b>—</b><small>—</small>', content)
        self.assertNotIn('+0,00%', content)

    def test_more_history_records_do_not_break_the_prose_budget(self):
        self.data['items'] *= 20
        content = build_content(self.data)
        self.assertEqual(content.count('<tr data-verified-row'), 40)
        self.assertLess(len(visible_main(content)), 800)
        self.assertIn('Giá đóng cửa', visible_main(content))

    def test_render_replaces_empty_legacy_page_preserving_auth_header(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            data_file = output / 'public/data/recommendation-history.json'
            data_file.parent.mkdir(parents=True)
            data_file.write_text(json.dumps(self.data), encoding='utf-8')
            source = '<head><script src="assets/app.js?v=old"></script></head><header data-auth>Account</header><section class="market-tape">Stale status</section><nav class="product-subnav">Old navigation</nav><main>Empty gate</main><footer>Footer</footer>'
            result = render_page(source, output)
            self.assertNotIn('Empty gate', result)
            self.assertNotIn('Stale status', result)
            self.assertNotIn('Old navigation', result)
            self.assertIn('<header data-auth>Account</header>', result)
            self.assertIn('data-recommendations', result)
            self.assertIn('data-recommendation-journal', result)
            self.assertIn('assets/app.js?v=20260905-verified-page', result)
            self.assertIn('verified-recommendations.js', result)


if __name__ == '__main__':
    unittest.main()
