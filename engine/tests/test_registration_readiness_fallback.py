import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RegistrationReadinessFallbackTests(unittest.TestCase):
    def test_transactional_auth_remains_open_when_product_email_is_pending(self):
        gate = (ROOT / "website" / "assets" / "auth-production-gate.js").read_text(encoding="utf-8")
        self.assertIn("transactionalAuthReady", gate)
        self.assertIn("config.configured === true", gate)
        self.assertIn("config.provider === 'supabase'", gate)
        self.assertIn("config.supabaseUrl", gate)
        self.assertIn("config.supabasePublishableKey", gate)
        self.assertIn("if (transactionalAuthReady)", gate)
        self.assertIn("return;", gate)
        self.assertNotIn("Đăng ký tài khoản mới sử dụng email xác minh", gate)
        self.assertNotIn("routeSignupLinksToInterest", gate)

    def test_public_copy_can_still_route_top_level_registration_through_plan_selection(self):
        source = (ROOT / "website" / "assets" / "public-copy-v7.js").read_text(encoding="utf-8")
        self.assertIn("emailDeliveryReady()", source)
        self.assertIn("emailDeliveryReady() ? 'signup/' : 'dang-ky/'", source)
        self.assertIn("if (!emailDeliveryReady()) return false", source)

    def test_registration_page_combines_plan_comparison_and_optional_premium_interest(self):
        page = (ROOT / "website" / "dang-ky" / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-proposition="plans"', page)
        self.assertIn("StockRadar Free", page)
        self.assertIn("StockRadar Premium", page)
        self.assertIn('href="signup/?plan=free"', page)
        self.assertIn('href="signup/?plan=premium"', page)
        self.assertIn("data-plan-comparison", page)
        self.assertIn("data-email-interest-form", page)
        self.assertIn("assets/email-interest.js", page)


if __name__ == "__main__":
    unittest.main()
