import json
import tempfile
import unittest
from pathlib import Path

from scripts import build_pages


ROOT = Path(__file__).resolve().parents[2]


class StaticRadarTickerPageTests(unittest.TestCase):
    def test_fail_closed_public_seed_generates_no_curated_ticker_routes(self):
        payload = json.loads((ROOT / "website" / "public" / "data" / "ticker-universe.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["data_status"], "BLOCKED_DATA_GATE")
        self.assertEqual(payload["public_scope"], "FAIL_CLOSED_NO_PUBLIC_TICKER_SEED")
        self.assertEqual(payload["items"], [])
        self.assertEqual(payload["internal_reference"]["record_count"], 405)

        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "site"
            build_pages.build(output)
            generated = {
                path.parent.name
                for path in (output / "co-phieu").glob("*/index.html")
                if path.parent.name != "demo1"
            }
            self.assertEqual(generated, set())
            self.assertTrue((output / "co-phieu" / "index.html").is_file())

    def test_generic_stock_route_remains_available_without_curated_seed(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "site"
            build_pages.build(output)
            page = (output / "co-phieu" / "index.html").read_text(encoding="utf-8")
            self.assertIn('data-dynamic-stock-report', page)
            self.assertIn('data-api-mode="auto"', page)
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
