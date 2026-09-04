import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "apply_buyer_readiness.py"

spec = importlib.util.spec_from_file_location("apply_buyer_readiness", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(module)


class PublicMethodJargonGateTests(unittest.TestCase):
    def transform(self, relative: str) -> str:
        source = (ROOT / relative).read_text(encoding="utf-8")
        return module.strip_analysis_jargon(source)

    def test_public_transform_removes_named_methods_from_core_pages(self):
        banned = (
            "4M",
            "CANSLIM",
            "SEPA",
            "VCP",
            "VPA",
            "RVOL",
            "Pocket Pivot",
            "Early Breakout",
            "Confirmed Breakout",
            "Payback",
            "Wyckoff",
            "Minervini",
            "O’Neil",
            "Phil Town",
            "Bear/Base/Bull",
            "Bear · Base · Bull",
            "Bear / Base / Bull",
        )
        pages = (
            "website/index.html",
            "website/radar5/index.html",
            "website/co-phieu/index.html",
            "website/dang-ky/index.html",
            "website/khuyen-nghi/index.html",
            "website/breakout/index.html",
        )
        for relative in pages:
            transformed = self.transform(relative)
            for term in banned:
                self.assertNotIn(term, transformed, f"{term} leaked in {relative}")

    def test_public_transform_keeps_action_outputs(self):
        page = self.transform("website/co-phieu/index.html")
        for marker in (
            "MUA hay CHỜ",
            "GIỮ, NHỒI, HẠ TỶ TRỌNG hay BÁN",
            "Buy Zone",
            "Stop-loss",
            "Target",
            "Risk/Reward",
        ):
            self.assertIn(marker, page)

    def test_radar_replaces_methodology_with_use_guide(self):
        radar = self.transform("website/radar5/index.html")
        for marker in (
            "CÁCH DÙNG RADAR",
            "Nhìn trạng thái, không cần học phương pháp.",
            "1. Chọn mã",
            "2. Chọn khung",
            "3. Xem trạng thái",
            "4. Quản trị rủi ro",
        ):
            self.assertIn(marker, radar)
        self.assertNotIn('id="phuong-phap"', radar)

    def test_public_transform_removes_setup_language(self):
        recommendations = self.transform("website/khuyen-nghi/index.html")
        self.assertNotIn("setup đạt chuẩn", recommendations)
        self.assertIn("điều kiện hành động đạt chuẩn", recommendations)


if __name__ == "__main__":
    unittest.main()
