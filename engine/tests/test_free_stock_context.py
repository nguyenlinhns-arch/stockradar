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

    def test_free_context_is_truthful_four_horizon_and_useful_while_decision_feed_is_closed(self):
        source = (ROOT / "website" / "assets" / "free-stock-context-v1.js").read_text(encoding="utf-8")
        market = (ROOT / "website" / "assets" / "public-market-reference-v1.js").read_text(encoding="utf-8")
        for marker in (
            "FREE · BỐI CẢNH STOCKRADAR",
            "5–20 phiên",
            "1–6 tháng",
            "6–18 tháng",
            "2–5 năm+",
            "Không bịa Fair Value, Buy Zone, Stop hay Target",
            "Không dùng tín hiệu/điểm của bên hiển thị tham chiếu làm tín hiệu StockRadar",
            "Không biến dữ liệu nghiên cứu nội bộ thành dữ liệu khách hàng khi chưa có quyền phát hành",
            "CHƯA PHÁT HÀNH MUA/BÁN",
            "ticker-universe.json",
            "DECISION FEED ĐANG CHỜ",
            "public-market-reference-v1.js",
            "public-market-reference-v1.css",
            "^[A-Z0-9]{3}$",
        ):
            self.assertIn(marker, source)
        for marker in (
            "DỮ LIỆU THỊ TRƯỜNG HIỂN THỊ TRỰC TIẾP",
            "TradingView",
            "StockRadar không tải xuống, xử lý hay dùng dữ liệu TradingView làm đầu vào",
            "embed-widget-symbol-info.js",
            "embed-widget-advanced-chart.js",
            "embed-widget-symbol-profile.js",
            "embed-widget-financials.js",
            "HOSE:${ticker}",
        ):
            self.assertIn(marker, market)
        self.assertNotIn("Radar 30", source)
        self.assertNotIn("Radar 30", market)

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
