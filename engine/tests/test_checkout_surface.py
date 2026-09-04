import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class CheckoutSurfaceTests(unittest.TestCase):
    def test_checkout_source_remains_stockradar_branded_and_authenticated(self):
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
            "Paused checkout leaked into live artifact",
        ):
            self.assertIn(marker, guard)
        self.assertNotIn("def paused_page", guard)
        self.assertNotIn("Premium checkout fail-closed", guard)
        self.assertNotIn("service_role", guard.lower())
        self.assertNotIn("sb_secret_", guard.lower())

    def test_premium_registration_routes_directly_to_payment_without_verification(self):
        plans = (ROOT / "website" / "dang-ky" / "index.html").read_text(encoding="utf-8")
        signup = (ROOT / "website" / "signup" / "index.html").read_text(encoding="utf-8")
        signup_client = (ROOT / "website" / "assets" / "signup-link-v1.js").read_text(encoding="utf-8")
        registration_guard = (ROOT / "scripts" / "enforce_registration_plan_ctas.py").read_text(encoding="utf-8")
        function = (ROOT / "supabase" / "functions" / "signup-link" / "index.ts").read_text(encoding="utf-8")

        self.assertIn('data-plan-free', plans)
        self.assertIn('data-plan-premium', plans)
        self.assertIn('signup/?plan=premium&next=thanh-toan/%3Fplan%3Dpremium', registration_guard)
        self.assertIn('Đăng ký & thanh toán', registration_guard)
        self.assertIn('không phải đăng ký Free trước', registration_guard)
        self.assertIn('assets/signup-link-v1.js', signup)
        self.assertNotIn('data-signup-email-sent', signup)
        self.assertNotIn('data-auth-signup-otp-form', signup)
        self.assertNotIn('xac-minh-email/', signup)
        self.assertIn("'thanh-toan/?plan=premium'", signup_client)
        self.assertIn('signInWithPassword', signup_client)
        self.assertIn('data-signup-existing-login', registration_guard)
        self.assertIn('auth.admin.createUser', function)
        self.assertIn('email_confirm: true', function)
        self.assertIn('Legacy Premium CTA leaked into final registration page', registration_guard)


if __name__ == "__main__":
    unittest.main()
