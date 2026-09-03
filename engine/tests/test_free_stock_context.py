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

    def test_free_context_is_truthful_and_four_horizon(self):
        source = (ROOT / "website" / "assets" / "free-stock-context-v1.js").read_text(encoding="utf-8")
        for marker in (
            "BẢN FREE · THÔNG TIN CÓ THỂ KẾT LUẬN",
            "5–20 phiên",
            "1–6 tháng",
            "6–18 tháng",
            "2–5 năm+",
            "Không dựng giá, định giá, Buy Zone, Stop hay Target",
            "Không biến danh sách Radar thành khuyến nghị mua",
            "CHƯA CÓ CƠ SỞ DỮ LIỆU ĐỦ ĐỂ ĐƯA RA HÀNH ĐỘNG MUA/BÁN",
        ):
            self.assertIn(marker, source)
        self.assertIn("ticker-universe.json", source)

    def test_free_context_does_not_duplicate_full_public_report(self):
        source = (ROOT / "website" / "assets" / "free-stock-context-v1.js").read_text(encoding="utf-8")
        self.assertIn(".position-detail-grid, .ticker-history, .evidence-grid", source)
        self.assertIn("data-free-stock-context", source)
        self.assertIn("MutationObserver", source)


if __name__ == "__main__":
    unittest.main()
