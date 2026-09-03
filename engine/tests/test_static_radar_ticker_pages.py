import json
import tempfile
import unittest
from pathlib import Path

from scripts import build_pages


ROOT = Path(__file__).resolve().parents[2]


class StaticRadarTickerPageTests(unittest.TestCase):
    def test_build_generates_only_public_radar_ticker_routes(self):
        expected = json.loads((ROOT / "website" / "public" / "data" / "ticker-universe.json").read_text(encoding="utf-8"))["items"]
        expected_tickers = {item["ticker"] for item in expected}
        self.assertEqual(len(expected_tickers), 30)

        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "site"
            build_pages.build(output)
            generated = {
                path.parent.name
                for path in (output / "co-phieu").glob("*/index.html")
                if path.parent.name != "demo1"
            }
            self.assertEqual(generated, expected_tickers)
            self.assertEqual(len(generated), 30)

    def test_generated_page_has_share_metadata_but_remains_noindex(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "site"
            build_pages.build(output)
            page = (output / "co-phieu" / "FPT" / "index.html").read_text(encoding="utf-8")
            self.assertIn('<base href="../../">', page)
            self.assertIn('<title>FPT — Phân tích Free &amp; Premium | StockRadar</title>', page)
            self.assertIn('<link rel="canonical" href="https://stockradar.vn/co-phieu/FPT/">', page)
            self.assertIn('<meta property="og:url" content="https://stockradar.vn/co-phieu/FPT/">', page)
            self.assertIn('data-static-ticker="FPT"', page)
            self.assertIn('name="robots" content="noindex,nofollow"', page)
            self.assertIn('data-api-mode="disabled"', page)

    def test_homepage_radar_links_are_rewritten_to_static_routes_only_in_build(self):
        source_home = (ROOT / "website" / "index.html").read_text(encoding="utf-8")
        self.assertIn("co-phieu/?ticker=FPT", source_home)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "site"
            build_pages.build(output)
            built_home = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn('href="co-phieu/FPT/"', built_home)
            self.assertNotIn("co-phieu/?ticker=FPT", built_home)


if __name__ == "__main__":
    unittest.main()
