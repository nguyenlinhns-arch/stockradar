from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class EmailSubscriptionFunnelTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_signup_collects_daily_and_action_alert_intent_without_prechecking(self):
        signup = self.read("website/signup/index.html")
        self.assertIn('name="email_daily_brief" type="checkbox"', signup)
        self.assertIn('name="email_event_alerts" type="checkbox"', signup)
        self.assertNotIn('name="email_daily_brief" type="checkbox" checked', signup)
        self.assertNotIn('name="email_event_alerts" type="checkbox" checked', signup)
        self.assertIn("assets/signup-email-intent.js", signup)

    def test_signup_auth_metadata_carries_legal_and_product_email_consent(self):
        client = self.read("website/assets/signup-email-intent.js")
        for key in (
            "terms_accepted",
            "terms_version",
            "privacy_accepted",
            "privacy_version",
            "product_email_consent",
            "product_email_consent_version",
            "product_email_daily_brief",
            "product_email_event_alerts",
        ):
            self.assertIn(key, client)

    def test_account_exposes_real_email_preference_center_and_ticker_alerts(self):
        account = self.read("website/tai-khoan/index.html")
        client = self.read("website/assets/email-preferences.js")
        self.assertIn("data-product-email-preferences", account)
        self.assertIn('name="daily_brief"', account)
        self.assertIn('name="event_alerts"', account)
        self.assertIn("assets/email-preferences.js", account)
        self.assertIn("product_email_preferences", client)
        self.assertIn("product_email_consent_events", client)
        self.assertIn("alert_enabled", client)
        self.assertIn("data-watchlist-alert-toggle", client)

    def test_signup_trigger_persists_preferences_and_consent_fail_closed(self):
        migration = self.read(
            "supabase/migrations/20260903064500_capture_signup_email_preferences_and_consent.sql"
        )
        self.assertIn("insert into public.product_email_preferences", migration.lower())
        self.assertIn("insert into public.product_email_consent_events", migration.lower())
        self.assertIn("'SIGNUP'", migration)
        self.assertIn("enabled,", migration)
        self.assertIn("false,", migration)
        self.assertIn("product_email_consent_version", migration)

    def test_homepage_has_email_conversion_surface(self):
        home = self.read("website/index.html")
        self.assertIn("data-email-conversion", home)
        self.assertIn("Đăng ký nhận email", home)
        self.assertIn("Báo cáo mỗi ngày + cảnh báo mua/bán", home)


if __name__ == "__main__":
    unittest.main()
