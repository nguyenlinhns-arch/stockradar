import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RegistrationReadinessFallbackTests(unittest.TestCase):
    def test_pending_email_state_routes_signup_to_plan_selection_instead_of_hiding(self):
        gate = (ROOT / "website" / "assets" / "auth-production-gate.js").read_text(encoding="utf-8")
        self.assertIn("routeSignupLinksToInterest", gate)
        self.assertIn("interestHref", gate)
        self.assertIn("dang-ky/", gate)
        self.assertNotIn("removeSignupLinks", gate)
        self.assertNotIn("link.hidden = true", gate)

    def test_public_copy_switches_registration_route_by_email_readiness(self):
        source = (ROOT / "website" / "assets" / "public-copy-v7.js").read_text(encoding="utf-8")
        self.assertIn("emailDeliveryReady()", source)
        self.assertIn("emailDeliveryReady() ? 'signup/' : 'dang-ky/'", source)
        self.assertIn("if (!emailDeliveryReady()) return false", source)

    def test_registration_page_is_plan_comparison_before_account_creation(self):
        page = (ROOT / "website" / "dang-ky" / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-proposition="plans"', page)
        self.assertIn("StockRadar Free", page)
        self.assertIn("StockRadar Premium", page)
        self.assertIn('href="signup/?plan=free"', page)
        self.assertIn('href="signup/?plan=premium"', page)
        self.assertIn("data-plan-comparison", page)
        self.assertNotIn("data-email-interest-form", page)


if __name__ == "__main__":
    unittest.main()
