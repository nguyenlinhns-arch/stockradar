from pathlib import Path
import importlib.util
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "redesign_home_value_block.py"

spec = importlib.util.spec_from_file_location("redesign_home_value_block", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(module)


class HomeDecisionV2Tests(unittest.TestCase):
    def test_new_block_is_compact_and_action_first(self):
        block = module.NEW_BLOCK
        for marker in (
            "STOCKRADAR TRẢ LỜI ĐIỀU GÌ?",
            "Nhập mã. Nhận ngay việc cần làm.",
            "CHƯA CÓ HÀNG",
            "MUA hay CHỜ",
            "ĐANG NẮM GIỮ",
            "GIỮ · TĂNG · GIẢM · BÁN",
            "MỐC HÀNH ĐỘNG",
            "Vùng mua · Stop · Target",
            "Tra cứu cổ phiếu",
            "4</b> khung đầu tư",
            "4</b> mốc rà soát/ngày",
            "100%</b> có dấu thời gian",
        ):
            self.assertIn(marker, block)

        for removed in (
            "BẠN TRẢ TIỀN ĐỂ NHẬN GÌ?",
            "Không phải thêm chỉ báo",
            "HỢP ĐỒNG ĐẦU RA PREMIUM",
            "buyer-first-grid",
            "buyer-contract",
        ):
            self.assertNotIn(removed, block)

    def test_script_replaces_legacy_home_block_and_adds_css(self):
        legacy = '''<html><head></head><body><section class="buyer-first-section" aria-labelledby="buyer-home-title"><div>OLD</div></section></body></html>'''
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            home = output / "index.html"
            home.write_text(legacy, encoding="utf-8")

            pattern = module.re.compile(
                r'<section class="buyer-first-section"\s+aria-labelledby="buyer-home-title">.*?</section>',
                flags=module.re.IGNORECASE | module.re.DOTALL,
            )
            source, count = pattern.subn(module.NEW_BLOCK, legacy, count=1)
            self.assertEqual(count, 1)
            css_tag = '<link rel="stylesheet" href="assets/home-decision-v2.css?v=20260904-decision2">\n'
            source = source.replace("</head>", css_tag + "</head>", 1)

            self.assertNotIn("buyer-first-section", source)
            self.assertNotIn("OLD", source)
            self.assertIn("home-decision-v2", source)
            self.assertIn("home-decision-v2.css", source)

    def test_css_is_responsive(self):
        css = (ROOT / "website" / "assets" / "home-decision-v2.css").read_text(encoding="utf-8")
        self.assertIn(".home-decision-v2-grid", css)
        self.assertIn("grid-template-columns:repeat(3,minmax(0,1fr))", css)
        self.assertIn("@media(max-width:900px)", css)
        self.assertIn("@media(max-width:620px)", css)


if __name__ == "__main__":
    unittest.main()
