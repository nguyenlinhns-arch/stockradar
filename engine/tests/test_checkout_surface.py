import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class CheckoutSurfaceTests(unittest.TestCase):
    def test_checkout_is_stockradar_branded_authenticated_and_fail_closed(self):
        page = (ROOT / "website" / "thanh-toan" / "index.html").read_text(encoding="utf-8")
        client = (ROOT / "website" / "assets" / "checkout-v1.js").read_text(encoding="utf-8")
        styles = (ROOT / "website" / "assets" / "checkout-v1.css").read_text(encoding="utf-8")

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
        ):
            self.assertIn(marker, page)

        for marker in (
            "create_my_checkout_request",
            "confirm_my_checkout_request",
            "get_my_checkout_request",
            "payment_reference",
            "checkout_enabled",
            "currentUser",
            "img.vietqr.io",
            "setInterval(refreshRequest, 8000)",
            "PAID",
            "EXPIRED",
        ):
            self.assertIn(marker, client)
        self.assertNotIn("service_role", client.lower())
        self.assertNotIn("sb_secret_", client.lower())
        self.assertIn("@media (max-width: 620px)", styles)
        self.assertIn("checkout-mobile-bar", styles)
        self.assertIn(".checkout-qr img", styles)

    def test_checkout_keeps_non_payment_fallback_until_bank_runtime_is_enabled(self):
        page = (ROOT / "website" / "thanh-toan" / "index.html").read_text(encoding="utf-8")
        email_client = (ROOT / "website" / "assets" / "email-interest.js").read_text(encoding="utf-8")

        for marker in (
            "data-checkout-disabled-fallback",
            "THANH TOÁN CHƯA ĐƯỢC KÍCH HOẠT",
            'data-email-interest-form',
            'name="event_alerts" type="checkbox" checked hidden',
            'name="privacy" type="checkbox" required',
            "assets/email-interest.js",
            "assets/lead-v1.css",
            'data-next-href="signup/?plan=premium"',
        ):
            self.assertIn(marker, page)

        self.assertIn("/functions/v1/email-interest", email_client)
        self.assertIn("privacy_accepted: true", email_client)
        self.assertIn("credentials: 'omit'", email_client)
        self.assertNotIn("service_role", page.lower())
        self.assertNotIn("service_role", email_client.lower())

    def test_plan_page_has_separate_registration_ctas(self):
        plans = (ROOT / "website" / "dang-ky" / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-plan-free', plans)
        self.assertIn('data-plan-premium', plans)
        self.assertIn('href="signup/?plan=free">Đăng ký</a>', plans)
        self.assertIn('href="signup/?plan=premium">Đăng ký</a>', plans)
        self.assertNotIn("Thanh toán / Nâng Premium", plans)


if __name__ == "__main__":
    unittest.main()
