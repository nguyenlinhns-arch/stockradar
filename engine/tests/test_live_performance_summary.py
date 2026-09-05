import unittest
from engine.stockradar.performance import live_publication_summary, PerformanceError


class LiveSummaryTests(unittest.TestCase):
    def row(self, key, value):
        return dict(recommendation_id=key, record_mode='LIVE_PUBLISHED', publish_status='PUBLISHED',
                    data_grade='DECISION_GRADE', is_mock=False, snapshot_id='fixture',
                    published_at='2026-08-01T03:00:00Z', activation_timestamp='2026-08-01T04:00:00Z',
                    close_timestamp='2026-08-11T04:00:00Z', close_price=100, final_return_pct=value)

    def test_keeps_losses_and_excludes_all_unreleased_cohorts(self):
        rows = [self.row('win', 10), self.row('loss', -5)]
        rows += [dict(self.row(mode, 99), record_mode=mode) for mode in ('SHADOW', 'MOCK', 'VERIFIED_EMAIL_HISTORY')]
        s = live_publication_summary(rows, minimum_closed=2)
        self.assertEqual((s['wins'], s['losses'], s['closed']), (1, 1, 2))
        self.assertEqual(s['expectancy_pct'], 2.5)
        self.assertEqual(s['payoff_ratio'], 2)
        self.assertEqual(s['median_holding_days'], 10)
        self.assertEqual(s['excluded_records'], 3)
        self.assertIsNone(s['max_drawdown_pct'])

    def test_small_sample_and_unactivated_have_no_fake_statistics(self):
        row = dict(self.row('waiting', 99), activation_timestamp=None)
        s = live_publication_summary([row, self.row('loss', -5)])
        self.assertEqual(s['unactivated'], 1)
        self.assertEqual(s['closed'], 1)
        self.assertEqual(s['sample_status'], 'INSUFFICIENT_SAMPLE')
        self.assertIsNone(s['win_rate_pct'])

    def test_duplicates_fail_instead_of_cherry_picking(self):
        with self.assertRaises(PerformanceError):
            live_publication_summary([self.row('same', 10), self.row('same', -5)])
