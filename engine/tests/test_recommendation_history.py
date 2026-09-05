import json
from pathlib import Path
import unittest

import pandas as pd

from scripts.build_recommendation_history import feature_at, reconcile_alerts, validate_history

ROOT = Path(__file__).resolve().parents[2]


class RecommendationHistoryTests(unittest.TestCase):
    def setUp(self):
        dates = pd.bdate_range('2024-01-01', periods=270)
        self.history = pd.DataFrame([dict(ticker='AAA', timestamp=str(d), open=100+i/10,
            close=100+i/10, high=101+i/10, low=99+i/10, volume=1000000+i)
            for i, d in enumerate(dates)])
        self.clean, _ = validate_history(self.history)

    def test_future_crash_cannot_change_prior_features(self):
        cutoff = self.clean.iloc[255].date
        baseline = feature_at(self.clean, cutoff)
        altered = self.clean.copy()
        later = altered.date > cutoff
        for col in ['open', 'high', 'low', 'close']:
            altered.loc[later, col] *= .25
        altered.loc[later, 'volume'] *= 100
        self.assertEqual(baseline, feature_at(altered, cutoff))

    def test_duplicate_sessions_fail_instead_of_selecting_a_price(self):
        with self.assertRaises(ValueError):
            validate_history(pd.concat([self.history, self.history.iloc[:1]]))

    def test_missing_session_is_not_forward_filled(self):
        day = self.clean.iloc[-1].date
        self.assertIsNone(feature_at(self.clean.iloc[:-1], day))

    def test_update_does_not_create_another_recommendation_or_fake_fill(self):
        ledger = json.loads((ROOT / 'track-record/verified-email-alerts.json').read_text(encoding='utf-8'))
        result = reconcile_alerts(ledger, self.clean, '2026-09-04')
        self.assertEqual(result['summary']['tickers'], 2)
        self.assertEqual(result['summary']['alerts'], 3)
        self.assertEqual(result['summary']['without_sell_email'], 2)
        self.assertIsNone(result['summary']['realized_return_pct'])
        self.assertTrue(all(r['price_change_pct'] is None for r in result['items']))
        self.assertTrue(all(r['execution_return_pct'] is None for r in result['items']))

    def test_sell_event_is_required_to_change_email_lifecycle(self):
        ledger = json.loads((ROOT / 'track-record/verified-email-alerts.json').read_text(encoding='utf-8'))
        sell = dict(ledger['events'][0], event_id='test-sell', kind='SELL', sent_at='2026-09-05T03:00:00Z')
        ledger['events'].append(sell)
        result = reconcile_alerts(ledger, self.clean, '2026-09-04')
        self.assertEqual(result['summary']['with_sell_email'], 1)
        self.assertEqual(result['summary']['without_sell_email'], 1)

    def test_public_audit_has_complete_day_grain_and_no_recipient_pii(self):
        text = (ROOT / 'website/public/data/recommendation-review-2026-08.json').read_text(encoding='utf-8')
        data = json.loads(text)
        self.assertEqual(len(data['days']), 31)
        self.assertEqual(len({r['date'] for r in data['days']}), 31)
        self.assertEqual(sum(len(d['candidates']) for d in data['days']), len(data['items']))
        self.assertIsNone(data['summary']['full_buy_criteria_verified'])
        self.assertTrue(all(not r['new_buy_allowed'] for r in data['items']))
        for name in ['recommendation-history.json','recommendation-review-2026-08.json']:
            content = (ROOT / 'website/public/data' / name).read_text(encoding='utf-8')
            self.assertNotIn('@gmail.com', content)
            self.assertNotIn('Message-Id', content)


if __name__ == '__main__':
    unittest.main()
