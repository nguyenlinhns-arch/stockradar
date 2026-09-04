from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WEBSITE = ROOT / "website"


class AuthSurfaceTests(unittest.TestCase):
    def test_signup_requires_email_password_and_legal_consent_without_verification(self) -> None:
        signup = (WEBSITE / "signup" / "index.html").read_text(encoding="utf-8")
        signup_client = (WEBSITE / "assets" / "signup-link-v1.js").read_text(encoding="utf-8")
        function = (ROOT / "supabase" / "functions" / "signup-link" / "index.ts").read_text(encoding="utf-8")
        policy = (WEBSITE / "assets" / "auth-policy.js").read_text(encoding="utf-8")

        for marker in ('type="email"', 'type="password"', 'assets/signup-link-v1.js', 'data-auth-signup-form'):
            self.assertIn(marker, signup)
        for forbidden in (
            'data-auth-signup-otp-form',
            'data-signup-email-sent',
            'autocomplete="one-time-code"',
            'Nhập mã OTP 6 số',
            'Kiểm tra email để xác minh tài khoản',
            'Đã xác minh? Đăng nhập',
            'xac-minh-email/',
        ):
            self.assertNotIn(forbidden, signup)

        self.assertIn('/functions/v1/signup-link', signup_client)
        self.assertIn('event.stopImmediatePropagation()', signup_client)
        self.assertIn('signInWithPassword', signup_client)
        self.assertIn("'thanh-toan/?plan=premium'", signup_client)
        self.assertNotIn('showEmailSent', signup_client)

        self.assertIn('auth.admin.createUser', function)
        self.assertIn('email_confirm: true', function)
        self.assertNotIn('auth.admin.generateLink', function)
        self.assertNotIn('RESEND_API_KEY', function)

        self.assertIn("dieu-khoan/", signup)
        self.assertIn("quyen-rieng-tu/", signup)
        self.assertIn("terms_accepted", policy)
        self.assertIn("privacy_accepted", policy)
        self.assertIn("const TERMS_VERSION = '2026-09-03'", policy)
        self.assertIn("const PRIVACY_VERSION = '2026-09-04'", policy)
        self.assertIn("terms_version: TERMS_VERSION", policy)
        self.assertIn("privacy_version: PRIVACY_VERSION", policy)

    def test_transactional_auth_email_is_launched_with_fail_closed_gate_available(self) -> None:
        config = (WEBSITE / "assets" / "auth-config.js").read_text(encoding="utf-8")
        gate = (WEBSITE / "assets" / "auth-email-gate.js").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
        self.assertIn("emailDeliveryReady: false", config)
        self.assertIn("emailDeliveryReady", gate)
        self.assertIn("data-auth-signup-form", gate)
        self.assertIn("data-auth-login-otp-form", gate)
        self.assertIn("data-auth-forgot-form", gate)
        self.assertIn("addEventListener('submit'", gate)
        self.assertIn("addEventListener('click'", gate)
        self.assertIn("stopImmediatePropagation", gate)
        self.assertIn("transactionalAuthReady", gate)
        self.assertIn("config.configured === true", gate)
        self.assertIn('STOCKRADAR_PRODUCT_EMAIL_READY: "0"', workflow)

    def test_unverified_users_can_resume_with_login_otp(self) -> None:
        # Login recovery may still offer OTP; the removed verification requirement is signup-only.
        login = (WEBSITE / "dang-nhap" / "index.html").read_text(encoding="utf-8")
        extra = (WEBSITE / "assets" / "auth-extra.js").read_text(encoding="utf-8")
        self.assertIn("data-auth-login-otp-form", login)
        self.assertIn("data-auth-login-otp-send", login)
        self.assertIn("one-time-code", login)
        self.assertIn("LOGIN_OTP_DEADLINE_KEY", extra)
        self.assertIn("client.auth.resend", extra)
        self.assertIn("client.auth.verifyOtp", extra)

    def test_signed_in_password_change_requires_current_password(self) -> None:
        account = (WEBSITE / "tai-khoan" / "index.html").read_text(encoding="utf-8")
        security = (WEBSITE / "assets" / "auth-account-security.js").read_text(encoding="utf-8")
        self.assertIn("data-require-current-password", account)
        self.assertIn('name="current_password"', account)
        self.assertIn("currentPassword", security)
        self.assertIn("stopImmediatePropagation", security)
        self.assertIn("password === currentPassword", security)

    def test_account_deletion_reauthenticates_before_backend_delete(self) -> None:
        account = (WEBSITE / "tai-khoan" / "index.html").read_text(encoding="utf-8")
        security = (WEBSITE / "assets" / "auth-delete-security.js").read_text(encoding="utf-8")
        self.assertIn("data-delete-account-form", account)
        self.assertIn("data-delete-account-reauth", account)
        self.assertIn('name="delete_current_password"', account)
        self.assertIn("XOA", account)
        self.assertIn("signInWithPassword", security)
        self.assertIn("DELETE_ACCOUNT", security)
        self.assertIn("client.functions.invoke('delete-account'", security)
        self.assertIn("stopImmediatePropagation", security)

    def test_legal_pages_exist_and_are_versioned(self) -> None:
        expected = {
            "dieu-khoan": "2026-09-03",
            "quyen-rieng-tu": "2026-09-04",
        }
        for route, version in expected.items():
            path = WEBSITE / route / "index.html"
            self.assertTrue(path.is_file(), route)
            source = path.read_text(encoding="utf-8")
            self.assertIn(version, source)
            self.assertIn("STOCKRADAR.VN", source)

    def test_public_auth_assets_never_contain_privileged_keys(self) -> None:
        paths = list((WEBSITE / "assets").glob("*.js")) + [ROOT / ".github" / "workflows" / "pages.yml"]
        for path in paths:
            source = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("sb_secret_", source, path)
            self.assertNotIn("service_role_key=", source, path)


if __name__ == "__main__":
    unittest.main()
