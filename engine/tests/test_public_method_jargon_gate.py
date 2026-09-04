import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUYER_SCRIPT = ROOT / "scripts" / "apply_buyer_readiness.py"
FINAL_SCRIPT = ROOT / "scripts" / "strip_public_methods.py"

buyer_spec = importlib.util.spec_from_file_location("apply_buyer_readiness", BUYER_SCRIPT)
buyer_module = importlib.util.module_from_spec(buyer_spec)
assert buyer_spec is not None and buyer_spec.loader is not None
buyer_spec.loader.exec_module(buyer_module)

final_spec = importlib.util.spec_from_file_location("strip_public_methods", FINAL_SCRIPT)
final_module = importlib.util.module_from_spec(final_spec)
assert final_spec is not None and final_spec.loader is not None
final_spec.loader.exec_module(final_module)


class PublicMethodJargonGateTests(unittest.TestCase):
    def transform(self, relative: str) -> str:
        source = (ROOT / relative).read_text(encoding="utf-8")
        source = buyer_module.strip_analysis_jargon(source)
        return final_module.rewrite(source)

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

    def test_public_transform_removes_analysis_method_and_setup_words(self):
        pages = (
            "website/index.html",
            "website/radar5/index.html",
            "website/co-phieu/index.html",
            "website/dang-ky/index.html",
            "website/khuyen-nghi/index.html",
            "website/breakout/index.html",
            "website/kiem-tra-co-phieu/index.html",
            "website/phan-tich/index.html",
        )
        for relative in pages:
            transformed = self.transform(relative).casefold()
            for term in ("phân tích", "phương pháp", "setup"):
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
            "Chỉ cần nhìn trạng thái và hành động.",
            "1. Chọn mã",
            "2. Chọn khung",
            "3. Xem trạng thái",
            "4. Quản trị rủi ro",
        ):
            self.assertIn(marker, radar)
        self.assertNotIn('id="phuong-phap"', radar)

    def test_public_transform_removes_setup_language(self):
        recommendations = self.transform("website/khuyen-nghi/index.html")
        self.assertNotIn("setup", recommendations.casefold())
        self.assertIn("điều kiện hành động đạt chuẩn", recommendations)

    def test_final_scrub_retires_analysis_route_and_rewrites_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output / "phan-tich").mkdir(parents=True)
            (output / "phan-tich" / "index.html").write_text("<h1>Phân tích cổ phiếu</h1>", encoding="utf-8")
            (output / "index.html").write_text(
                '<a href="phan-tich/">Phân tích chuyên sâu</a>', encoding="utf-8"
            )

            legacy = output / "phan-tich"
            if legacy.exists():
                import shutil
                shutil.rmtree(legacy)
            source = final_module.rewrite((output / "index.html").read_text(encoding="utf-8"))
            (output / "index.html").write_text(source, encoding="utf-8")

            self.assertFalse(legacy.exists())
            self.assertNotIn("phân tích", source.casefold())
            self.assertNotIn("phương pháp", source.casefold())
            self.assertNotIn("setup", source.casefold())
            self.assertNotIn("phan-tich/", source)
            self.assertIn("kiem-tra-co-phieu/", source)


if __name__ == "__main__":
    unittest.main()
