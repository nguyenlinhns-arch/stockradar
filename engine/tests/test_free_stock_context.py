import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class FreeStockContextTests(unittest.TestCase):
    def test_stock_page_loads_free_context_assets(self):
        page = (ROOT / "website" / "co-phieu" / "index.html").read_text(encoding="utf-8")
        self.assertIn("assets/free-stock-context-v1.css", page)
        self.assertIn("assets/free-stock-context-v1.js", page)
        self.assertIn("analysis-tier-free", page)
        self.assertIn("analysis-tier-premium", page)
        self.assertIn("Radar toàn HOSE", page)
        self.assertNotIn("Radar 30", page)

    def test_free_context_is_truthful_and_four_horizon(self):
        source = (ROOT / "website" / "assets" / "free-stock-context-v1.js").read_text(encoding="utf-8")
        for marker in (
            "BẢN FREE · BỐI CẢNH CÓ THỂ PHÁT HÀNH",
            "5–20 phiên",
            "1–6 tháng",
            "6–18 tháng",
            "2–5 năm+",
            "Không bịa giá, Fair Value, Buy Zone, Stop hay Target",
            "Không biến thứ hạng Radar thành khuyến nghị mua",
            "Không coi dữ liệu nội bộ là dữ liệu được phép phát hành",
            "CHƯA PHÁT HÀNH TÍN HIỆU MUA/BÁN CHO SNAPSHOT CÔNG KHAI NÀY",
        ):
            self.assertIn(marker, source)
        self.assertIn("ticker-universe.json", source)
        self.assertIn("CHỜ GATE PHÁT HÀNH", source)
        self.assertIn("^[A-Z0-9]{3}$", source)
        self.assertNotIn("Radar 30", source)

    def test_free_context_replaces_technical_fallback_and_yields_to_full_report(self):
        source = (ROOT / "website" / "assets" / "free-stock-context-v1.js").read_text(encoding="utf-8")
        styles = (ROOT / "website" / "assets" / "free-stock-context-v1.css").read_text(encoding="utf-8")
        self.assertIn(".position-detail-grid, .ticker-history, .evidence-grid", source)
        self.assertIn("clearFallback", source)
        self.assertIn("has-free-context", source)
        self.assertIn("data-free-stock-context", source)
        self.assertIn("MutationObserver", source)
        self.assertIn(".analysis-free-content.has-free-context>.ticker-accepted", styles)
        self.assertIn(".analysis-free-content.has-free-context>.data-readiness", styles)
        self.assertIn("display:none!important", styles)


if __name__ == "__main__":
    unittest.main()
