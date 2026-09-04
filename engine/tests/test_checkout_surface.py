import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class CheckoutSurfaceTests(unittest.TestCase):
    def test_checkout_is_stockradar_branded_and_fail_closed(self):
        page = (ROOT / "website" / "thanh-toan" / "index.html").read_text(encoding="utf-8")
        client = (ROOT / "website" / "assets" / "checkout-v1.js").read_text(encoding="utf-8")
        styles = (ROOT / "website" / "assets" / "checkout-v1.css").read_text(encoding="utf-8")

        for marker in (
            'data-proposition="checkout"',
            "StockRadar Premium",
            "VietQR / Chuyển khoản ngân hàng",
            "199.000đ",
            "30 ngày",
            "Không tự gia hạn",
            "data-checkout-confirm",
            "data-checkout-account-email",
            "assets/checkout-v1.css",
            "assets/checkout-v1.js",
        ):
            self.assertIn(marker, page)

        self.assertIn("enabled: false", client)
        self.assertIn("paymentReference", client)
        self.assertIn("checkout.enabled", client)
        self.assertIn("currentUser", client)
        self.assertNotIn("service_role", client.lower())
        self.assertNotIn("secret", client.lower())
        self.assertIn("@media (max-width: 620px)", styles)
        self.assertIn("checkout-mobile-bar", styles)

    def test_disabled_checkout_has_non_payment_premium_interest_fallback(self):
        page = (ROOT / "website" / "thanh-toan" / "index.html").read_text(encoding="utf-8")
        email_client = (ROOT / "website" / "assets" / "email-interest.js").read_text(encoding="utf-8")

        for marker in (
            "CỔNG THANH TOÁN CHƯA MỞ",
            "Đăng ký ưu tiên Premium thay vì chờ",
            'data-email-interest-form',
            'name="event_alerts" type="checkbox" checked hidden',
            'name="privacy" type="checkbox" required',
            "Báo tôi khi Premium mở thanh toán",
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

    def test_premium_plan_routes_to_checkout(self):
        plans = (ROOT / "website" / "dang-ky" / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="thanh-toan/?plan=premium"', plans)
        self.assertIn("Thanh toán / Nâng Premium", plans)


if __name__ == "__main__":
    unittest.main()
