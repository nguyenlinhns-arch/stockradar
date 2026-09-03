import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class StockPageContextTests(unittest.TestCase):
    def test_stock_page_loads_ticker_context_script(self):
        page = (ROOT / "website" / "co-phieu" / "index.html").read_text(encoding="utf-8")
        self.assertIn("assets/stock-page-context-v1.js", page)
        self.assertIn('id="free-analysis-title"', page)
        self.assertIn('id="premium-analysis-title"', page)

    def test_ticker_context_labels_page_and_both_tiers(self):
        source = (ROOT / "website" / "assets" / "stock-page-context-v1.js").read_text(encoding="utf-8")
        self.assertIn("Phân tích ${ticker}", source)
        self.assertIn("Free · ${ticker}", source)
        self.assertIn("Premium · ${ticker}", source)
        self.assertIn("bốn khung đầu tư", source)
        self.assertIn("Phân tích Free & Premium | StockRadar", source)


if __name__ == "__main__":
    unittest.main()
