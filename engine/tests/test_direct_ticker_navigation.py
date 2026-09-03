import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class DirectTickerNavigationTests(unittest.TestCase):
    def test_search_routes_to_analysis_in_one_interaction(self):
        source = (ROOT / "website" / "assets" / "direct-ticker-nav-v1.js").read_text(encoding="utf-8")
        for marker in (
            "[data-stock-search-form]",
            "[data-ticker-value]",
            "co-phieu/?ticker=",
            "window.location.assign",
            "kiem-tra-co-phieu",
            "phan-tich",
        ):
            self.assertIn(marker, source)
        self.assertIn("/^[A-Z]{3}$/", source)
        self.assertIn("setTimeout(() => navigate(ticker), 0)", source)

    def test_pages_injector_loads_direct_navigation(self):
        source = (ROOT / "scripts" / "inject_public_ux.py").read_text(encoding="utf-8")
        self.assertIn('"direct-ticker-nav-v1.js"', source)
        self.assertIn("direct_ticker_js", source)
        self.assertIn("20260903-direct1", source)

    def test_primary_search_surfaces_exist(self):
        for relative in (
            "website/index.html",
            "website/kiem-tra-co-phieu/index.html",
            "website/phan-tich/index.html",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("data-stock-search-form", source, relative)
            self.assertIn('name="ticker"', source, relative)


if __name__ == "__main__":
    unittest.main()
