from pathlib import Path
import importlib.util
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("apply_conversion_v3", ROOT / "scripts" / "apply_conversion_v3.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ConversionV3Tests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_homepage_becomes_lookup_first(self) -> None:
        transformed = MODULE.transform_home(self.read("website/index.html"))
        self.assertIn("Bạn đang quan tâm mã nào?", transformed)
        self.assertIn("Tra mã miễn phí", transformed)
        self.assertIn("conversion-search-only", transformed)
        self.assertIn("Không cần tài khoản chứng khoán", transformed)
        self.assertNotIn("buyer-start-card", transformed)

    def test_stock_page_has_contextual_premium_preview(self) -> None:
        transformed = MODULE.transform_stock(self.read("website/co-phieu/index.html"), checkout_ready=False)
        for marker in (
            "BẢN XEM TRƯỚC PREMIUM", "Mở quyết định đầy đủ cho mã bạn vừa tra",
            "MUA / CHỜ", "GIỮ / TĂNG / GIẢM / BÁN", "Vùng mua", "Stop / vô hiệu",
            "Target", "data-premium-conversion-cta", "Tạo tài khoản Premium",
        ):
            self.assertIn(marker, transformed)
        self.assertIn("data-premium-stock-report", transformed)
        self.assertIn("data-premium-gate-copy", transformed)

    def test_pricing_is_short_and_value_first(self) -> None:
        transformed = MODULE.transform_plans(self.read("website/dang-ky/index.html"), checkout_ready=False)
        # The source is intentionally commercial and concise: two plans plus one comparison table.
        for marker in (
            "data-plan-free", "data-plan-premium", "data-plan-comparison",
            "StockRadar Free", "StockRadar Premium", "199.000đ",
            "Mua mới", "Đang nắm giữ", "Buy Zone", "không tự gia hạn",
        ):
            self.assertIn(marker, transformed)
        # Do not reintroduce the retired explanatory block merely to satisfy an old test contract.
        self.assertNotIn("Bốn thứ trực tiếp giúp bạn ra quyết định", transformed)
        self.assertNotIn("299.000", transformed)

    def test_signup_keeps_paid_email_consent_optional_and_supports_premium_fast_path(self) -> None:
        transformed = MODULE.transform_signup(self.read("website/signup/index.html"))
        self.assertIn("data-premium-flow-summary", transformed)
        self.assertIn("Tùy chọn email Premium", transformed)
        self.assertIn("Free chỉ nhận email hệ thống", transformed)
        js = self.read("website/assets/conversion-v3.js")
        self.assertIn("params.get('plan') === 'premium'", js)
        self.assertIn("premium.checked = true", js)
        self.assertNotIn("email_event_alerts.checked = true", js)
        self.assertNotIn("daily_brief.checked = true", js)

    def test_performance_puts_results_before_explanation(self) -> None:
        transformed = MODULE.transform_performance(self.read("website/hieu-qua/index.html"))
        self.assertIn("KẾT QUẢ TRƯỚC, CÁCH ĐO SAU", transformed)
        self.assertLess(transformed.index("conversion-performance-head"), transformed.index("BẰNG CHỨNG TRƯỚC KHI TRẢ PHÍ"))

    def test_my_stockradar_and_responsive_assets_exist(self) -> None:
        transformed = MODULE.transform_account(self.read("website/tai-khoan/index.html"))
        self.assertIn("My StockRadar", transformed)
        self.assertIn("Biến watchlist thành trung tâm quyết định cá nhân", transformed)
        self.assertIn("ƯU TIÊN THEO DÕI", transformed)
        css = self.read("website/assets/conversion-v3.css")
        self.assertIn(".premium-preview-grid", css)
        self.assertIn(".my-stockradar-grid", css)
        self.assertIn("@media(max-width:620px)", css)


if __name__ == "__main__":
    unittest.main()
