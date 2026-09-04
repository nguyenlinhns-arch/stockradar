import json
import tempfile
import unittest
from pathlib import Path

from scripts import build_pages
from scripts.fail_close_public_ticker_seed import fail_close


ROOT = Path(__file__).resolve().parents[2]


class StaticRadarTickerPageTests(unittest.TestCase):
    def test_fail_close_transform_removes_curated_ticker_seed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ticker-universe.json"
            path.write_text(json.dumps({
                "schema_version": "2.1.2",
                "snapshot_id": "hose-universe-2026-09-02-065632-vn",
                "as_of": "2026-09-02T06:56:32+07:00",
                "data_status": "BLOCKED_DATA_GATE",
                "public_scope": "REFERENCE_ONLY",
                "internal_reference": {
                    "record_count": 405,
                    "validated_count": 405,
                    "raw_publication_allowed": False,
                },
                "items": [{"ticker": "AAA"}, {"ticker": "BBB"}],
            }), encoding="utf-8")
            payload = fail_close(path)
            self.assertEqual(payload["data_status"], "BLOCKED_DATA_GATE")
            self.assertEqual(payload["public_scope"], "FAIL_CLOSED_NO_PUBLIC_TICKER_SEED")
            self.assertEqual(payload["items"], [])
            self.assertEqual(payload["internal_reference"]["record_count"], 405)

    def test_generic_stock_route_remains_fail_closed_until_production_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "site"
            build_pages.build(output)
            page = (output / "co-phieu" / "index.html").read_text(encoding="utf-8")
            self.assertIn('data-dynamic-stock-report', page)
            self.assertIn('data-api-mode="disabled"', page)
            self.assertNotIn('data-static-ticker="FPT"', page)

    def test_homepage_contains_no_fixed_ticker_links_before_or_after_build(self):
        source_home = (ROOT / "website" / "index.html").read_text(encoding="utf-8")
        self.assertIn("data-live-radar-home", source_home)
        self.assertNotIn("co-phieu/?ticker=", source_home)
        self.assertNotIn("Radar 30", source_home)

        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "site"
            build_pages.build(output)
            built_home = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("data-live-radar-home", built_home)
            self.assertNotIn("co-phieu/?ticker=", built_home)
            self.assertNotIn("Radar 30", built_home)


if __name__ == "__main__":
    unittest.main()
