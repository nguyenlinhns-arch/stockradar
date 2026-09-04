import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RadarMethodologyPublicTests(unittest.TestCase):
    def test_radar_source_documents_eight_operational_layers(self):
        page = (ROOT / "website" / "radar5" / "index.html").read_text(encoding="utf-8")
        required = (
            'id="phuong-phap"',
            "mỗi mã phải đi qua 8 lớp",
            "1. Dữ liệu &amp; khả năng giao dịch",
            "2. 4M &amp; Payback",
            "3. CANSLIM &amp; tăng trưởng",
            "4. Định giá đa kịch bản",
            "5. Market &amp; Sector Regime",
            "6. SEPA / VCP / Stage",
            "7. VPA · RVOL · dòng tiền lớn",
            "8. Risk &amp; Action Gate",
            "Quét toàn HOSE trước",
            "Full-Scan Gate",
            "RVOL/same-time volume",
            "Catalyst/corporate actions chỉ được cộng điểm khi nguồn đủ mới và đủ tin cậy",
        )
        for marker in required:
            self.assertIn(marker, page)

        self.assertNotIn("4 phương pháp cốt lõi", page)
        self.assertNotIn("30 mã", page)
        self.assertNotIn("10 ngành · 3 mã", page)

    def test_methodology_styles_are_responsive(self):
        css = (ROOT / "website" / "assets" / "site-v4.css").read_text(encoding="utf-8")
        self.assertIn(".site-v4 .radar-method-grid", css)
        self.assertIn(".site-v4 .radar-vietnam-note", css)
        self.assertIn("@media(max-width:760px)", css)


if __name__ == "__main__":
    unittest.main()
