import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RegistrationReadinessFallbackTests(unittest.TestCase):
    def test_pending_email_state_routes_signup_to_interest_instead_of_hiding(self):
        gate = (ROOT / "website" / "assets" / "auth-production-gate.js").read_text(encoding="utf-8")
        self.assertIn("routeSignupLinksToInterest", gate)
        self.assertIn("interestHref", gate)
        self.assertIn("dang-ky/", gate)
        self.assertIn("Đăng ký quan tâm Premium", gate)
        self.assertNotIn("removeSignupLinks", gate)
        self.assertNotIn("link.hidden = true", gate)

    def test_public_copy_switches_registration_route_by_email_readiness(self):
        source = (ROOT / "website" / "assets" / "public-copy-v7.js").read_text(encoding="utf-8")
        self.assertIn("emailDeliveryReady()", source)
        self.assertIn("emailDeliveryReady() ? 'signup/' : 'dang-ky/'", source)
        self.assertIn("if (!emailDeliveryReady()) return false", source)
        self.assertIn("Đăng ký quan tâm", source)

    def test_interest_page_is_premium_interest_not_free_daily_email(self):
        page = (ROOT / "website" / "dang-ky" / "index.html").read_text(encoding="utf-8")
        client = (ROOT / "website" / "assets" / "email-interest.js").read_text(encoding="utf-8")
        self.assertIn("Đăng ký quan tâm Premium", page)
        self.assertIn("báo cáo Premium hằng ngày", page)
        self.assertIn("cảnh báo hành động Premium", page)
        self.assertIn("Free không nhận email báo cáo/khuyến nghị hằng ngày", page)
        self.assertIn("Báo cáo Premium hằng ngày", client)
        self.assertIn("Cảnh báo hành động Premium", client)
        self.assertNotIn("Nhận bản rà soát thị trường cơ bản hằng ngày", page)


if __name__ == "__main__":
    unittest.main()
