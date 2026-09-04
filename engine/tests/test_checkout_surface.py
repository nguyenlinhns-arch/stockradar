import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class CheckoutSurfaceTests(unittest.TestCase):
    def test_checkout_is_stockradar_branded_authenticated_and_live_ready(self):
        page = (ROOT / "website" / "thanh-toan" / "index.html").read_text(encoding="utf-8")
        client = (ROOT / "website" / "assets" / "checkout-v1.js").read_text(encoding="utf-8")
        styles = (ROOT / "website" / "assets" / "checkout-v1.css").read_text(encoding="utf-8")
        fixed_qr = ROOT / "website" / "assets" / "vpbank-qr-static.svg"

        for marker in (
            'data-proposition="checkout"',
            "StockRadar Premium",
            "VietQR",
            "199.000đ",
            "30 ngày",
            "Không tự gia hạn",
            "data-checkout-confirm",
            "data-checkout-account-email",
            "data-checkout-qr-image",
            "data-checkout-expiry",
            "assets/auth-config.js",
            "assets/checkout-v1.css",
            "assets/checkout-v1.js",
            "VPBank",
            "0934389822",
        ):
            self.assertIn(marker, page)

        for marker in (
            "create_my_checkout_request",
            "confirm_my_checkout_request",
            "get_my_checkout_request",
            "payment_reference",
            "checkout_enabled",
            "currentUser",
            "setInterval(refreshRequest, 8000)",
            "PAID",
            "EXPIRED",
        ):
            self.assertIn(marker, client)
        self.assertTrue(fixed_qr.is_file())
        self.assertIn("VPBank VietQR", fixed_qr.read_text(encoding="utf-8"))
        self.assertNotIn("service_role", client.lower())
        self.assertNotIn("sb_secret_", client.lower())
        self.assertIn("@media (max-width: 620px)", styles)
        self.assertIn("checkout-mobile-bar", styles)
        self.assertIn(".checkout-qr img", styles)

    def test_commercial_checkout_is_opened_by_final_pages_guard(self):
        page = (ROOT / "website" / "thanh-toan" / "index.html").read_text(encoding="utf-8")
        guard = (ROOT / "scripts" / "enforce_checkout_public_bank_info.py").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
        fast_workflow = (ROOT / ".github" / "workflows" / "pages-fast-hotfix.yml").read_text(encoding="utf-8")

        for marker in (
            "data-checkout-disabled-fallback",
            "data-checkout-confirm",
            "assets/checkout-v1.js",
            "assets/auth-config.js",
        ):
            self.assertIn(marker, page)

        self.assertIn('STOCKRADAR_CHECKOUT_READY: "1"', workflow)
        self.assertIn('STOCKRADAR_CHECKOUT_READY: "1"', fast_workflow)
        for marker in (
            "Premium checkout opened with owner VPBank QR",
            "vpbank-qr-static.svg",
            "VPBank",
            "0934389822",
        ):
            self.assertIn(marker, guard)
        for stale in (
            "Premium checkout fail-closed",
            'data-checkout-ready="false"',
            "Premium tạm dừng kích hoạt mới",
        ):
            self.assertNotIn(stale, guard)
        self.assertNotIn("service_role", guard.lower())
        self.assertNotIn("sb_secret_", guard.lower())

    def test_plan_page_has_separate_registration_ctas(self):
        plans = (ROOT / "website" / "dang-ky" / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-plan-free', plans)
        self.assertIn('data-plan-premium', plans)
        self.assertIn('href="signup/?plan=free">Đăng ký</a>', plans)
        self.assertIn('href="signup/?plan=premium">Đăng ký</a>', plans)
        self.assertNotIn("Thanh toán / Nâng Premium", plans)


if __name__ == "__main__":
    unittest.main()
