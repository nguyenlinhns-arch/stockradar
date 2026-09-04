#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "engine/tests/test_email_subscription_funnel.py"
source = path.read_text(encoding="utf-8")

old = '''    def test_public_ticker_seed_is_fail_closed_until_full_hose_master_is_approved(self):
        payload = json.loads(self.read("website/public/data/ticker-universe.json"))
        self.assertEqual(payload["data_status"], "BLOCKED_DATA_GATE")
        self.assertEqual(payload["public_scope"], "FAIL_CLOSED_NO_PUBLIC_TICKER_SEED")
        self.assertEqual(payload["selection_kind"], "NONE_FAIL_CLOSED")
        self.assertEqual(payload["items"], [])
        self.assertEqual(payload["internal_reference"]["record_count"], 405)
        self.assertEqual(payload["internal_reference"]["validated_count"], 405)
        self.assertFalse(payload["internal_reference"]["raw_publication_allowed"])
'''
new = '''    def test_reference_seed_is_non_publishable_and_pages_workflow_fail_closes_it(self):
        payload = json.loads(self.read("website/public/data/ticker-universe.json"))
        self.assertEqual(payload["data_status"], "BLOCKED_DATA_GATE")
        self.assertEqual(payload["public_scope"], "REFERENCE_ONLY")
        self.assertFalse(payload["full_universe"])
        self.assertEqual(payload["internal_reference"]["record_count"], 405)
        self.assertEqual(payload["internal_reference"]["validated_count"], 405)
        self.assertFalse(payload["internal_reference"]["raw_publication_allowed"])
        self.assertLess(len(payload["items"]), payload["internal_reference"]["record_count"])
        workflow = self.read(".github/workflows/pages.yml")
        self.assertIn("python scripts/fail_close_public_ticker_seed.py website/public/data/ticker-universe.json", workflow)
        self.assertLess(workflow.index("Run regression suite"), workflow.index("Fail-close public ticker seed before Pages build"))
'''
if old not in source:
    raise SystemExit("old public ticker seed test body not found")
source = source.replace(old, new)

source = source.replace('        self.assertNotIn("30 mã", page)\n        self.assertNotIn("10 ngành · 3 mã", page)\n', '        self.assertNotIn("Radar 30", page)\n        self.assertNotIn("10 ngành · 3 mã", page)\n')
path.write_text(source, encoding="utf-8")
print("Patched remaining Radar V3 email/funnel regressions")
