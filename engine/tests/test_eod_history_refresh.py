import unittest
from datetime import date
from scripts.refresh_eod_email_history import eligible_run


class EodHistoryRefreshTests(unittest.TestCase):
    def test_only_successful_main_post_close_collector_is_eligible(self):
        run = dict(conclusion='success', head_branch='main', path='.github/workflows/hose-data-bootstrap.yml',
                   event='schedule', run_started_at='2026-09-04T08:25:00Z')
        self.assertTrue(eligible_run(run, date(2026, 9, 4)))
        for extra in [dict(conclusion='failure'), dict(head_branch='feature'), dict(event='pull_request'),
                      dict(path='.github/workflows/other.yml'), dict(run_started_at='2026-09-04T07:15:00Z'),
                      dict(run_started_at='2026-09-03T08:25:00Z')]:
            self.assertFalse(eligible_run({**run, **extra}, date(2026, 9, 4)), extra)
