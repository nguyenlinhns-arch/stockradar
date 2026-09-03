import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RadarMethodologyPublicTests(unittest.TestCase):
    def test_radar_keeps_four_methods_compact_and_vietnam_specific(self):
        page = (ROOT / "website" / "radar5" / "index.html").read_text(encoding="utf-8")
        required = (
            'id="phuong-phap"',
            "4 phương pháp cốt lõi",
            "4M &amp; Payback — Phil Town",
            "CANSLIM — William J. O’Neil",
            "SEPA / VCP — Mark Minervini",
            "VPA / Wyckoff — Anna Coulling &amp; Richard D. Wyckoff",
            "Áp dụng Việt Nam",
            "HOSE · thanh khoản · free float",
            "RVOL/same-time volume",
            "Pocket Pivot — Gil Morales &amp; Chris Kacher",
        )
        for marker in required:
            self.assertIn(marker, page)

        for removed in (
            "StockRadar rà soát cổ phiếu như thế nào?",
            "Không dùng một chỉ báo đơn lẻ",
            "Có áp dụng được tại thị trường Việt Nam?",
            "Bốn phương pháp được kết hợp",
        ):
            self.assertNotIn(removed, page)

    def test_methodology_styles_are_four_column_and_responsive(self):
        css = (ROOT / "website" / "assets" / "site-v4.css").read_text(encoding="utf-8")
        self.assertIn(".site-v4 .radar-method-grid{grid-template-columns:repeat(4,minmax(0,1fr))}", css)
        self.assertIn(".site-v4 .radar-vietnam-note", css)
        self.assertIn("@media(max-width:760px)", css)


if __name__ == "__main__":
    unittest.main()
