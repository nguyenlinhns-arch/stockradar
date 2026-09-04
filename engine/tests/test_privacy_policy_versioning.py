import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class PrivacyPolicyVersioningTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_terms_and_privacy_versions_are_recorded_separately(self):
        source = self.read("website/assets/signup-email-intent.js")
        self.assertIn("const TERMS_VERSION = '2026-09-03'", source)
        self.assertIn("const PRIVACY_VERSION = '2026-09-04'", source)
        self.assertIn("const PRODUCT_EMAIL_CONSENT_VERSION = '2026-09-04'", source)
        self.assertIn("terms_version: TERMS_VERSION", source)
        self.assertIn("privacy_version: PRIVACY_VERSION", source)
        self.assertIn("product_email_consent_version: PRODUCT_EMAIL_CONSENT_VERSION", source)

    def test_public_email_interest_uses_current_privacy_version(self):
        source = self.read("website/assets/email-interest.js")
        self.assertIn("const CONSENT_VERSION = '2026-09-04'", source)
        for page in (
            "website/nhan-ban-tin/index.html",
            "website/dang-ky/index.html",
        ):
            html = self.read(page)
            self.assertIn("Chính sách quyền riêng tư", html)
            self.assertIn("2026-09-04", html)

        # Checkout is live but does not collect a second pre-auth email consent.
        # It still exposes the site's privacy policy and uses authenticated account state.
        checkout = self.read("website/thanh-toan/index.html")
        self.assertIn('href="quyen-rieng-tu/"', checkout)
        self.assertIn("data-checkout-account-email", checkout)
        self.assertIn("data-checkout-confirm", checkout)

    def test_account_center_uses_current_email_consent_and_per_ticker_alert_controls(self):
        email_source = self.read("website/assets/email-preferences.js")
        watch_source = self.read("website/assets/account-preferences.js")
        self.assertIn("const CONSENT_VERSION = '2026-09-04'", email_source)
        self.assertIn("source: 'ACCOUNT_CENTER'", email_source)
        self.assertIn("data-watchlist-alert", watch_source)
        self.assertIn("alert_enabled: next", watch_source)
        self.assertIn("Cảnh báo theo từng mã chỉ dành cho Trial/Premium", watch_source)

    def test_privacy_policy_discloses_api_audit_and_account_deletion_retention(self):
        privacy = self.read("website/quyen-rieng-tu/index.html")
        self.assertIn("Phiên bản: 2026-09-04", privacy)
        self.assertIn("Nhật ký vận hành API", privacy)
        self.assertIn("không lưu JWT/Authorization token", privacy)
        self.assertIn("xác thực lại gần thời điểm xóa", privacy)
        self.assertIn("liên kết trực tiếp tới tài khoản bị xóa được tách", privacy)
        self.assertIn("consent cũ không được tự động coi là consent cho phiên bản mới", privacy)

    def test_database_current_email_consent_is_bumped_fail_closed(self):
        migration = self.read("supabase/migrations/20260904043953_bump_privacy_email_consent_version_20260904.sql")
        self.assertIn("current_consent_version = '2026-09-04'", migration)
        self.assertIn("set enabled = false", migration.lower())
        self.assertIn("event.document_version = '2026-09-04'", migration)
        self.assertNotIn("sending_enabled = true", migration.lower())


if __name__ == "__main__":
    unittest.main()
