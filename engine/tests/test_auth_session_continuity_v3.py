from pathlib import Path
import tempfile
import unittest

from scripts import build_pages


ROOT = Path(__file__).resolve().parents[2]
WEBSITE = ROOT / "website"


class AuthSessionContinuityV3Tests(unittest.TestCase):
    def test_public_pages_receive_shared_auth_state_even_when_config_already_exists(self) -> None:
        previous = build_pages.AUTH_ENABLED
        build_pages.AUTH_ENABLED = True
        try:
            with tempfile.TemporaryDirectory() as temp:
                output = Path(temp) / "site"
                output.mkdir(parents=True)
                home = output / "index.html"
                source = '<html><head><script src="assets/auth-config.js"></script></head><body></body></html>'
                rendered = build_pages.inject_auth_bundle(source, home, output)
                self.assertEqual(rendered.count("assets/auth-config.js"), 1)
                self.assertIn("assets/auth-state-v2.js", rendered)
                self.assertNotIn("@supabase/supabase-js", rendered)
                self.assertNotIn("assets/auth.js", rendered)
        finally:
            build_pages.AUTH_ENABLED = previous

    def test_shared_auth_state_migrates_legacy_storage_without_deleting_valid_session(self) -> None:
        source = (WEBSITE / "assets" / "auth-state-v2.js").read_text(encoding="utf-8")
        self.assertIn("const secondaryValue = localStorage.getItem(secondary)", source)
        self.assertIn("else if (secondaryValue)", source)
        self.assertIn("localStorage.setItem(STORAGE_KEY, secondaryValue)", source)
        self.assertNotIn("else {\n        localStorage.removeItem(secondary);", source)
        self.assertIn("auth.auth.getSession()", source)
        self.assertIn("storage: window.localStorage", source)

    def test_shared_auth_state_creates_account_actions_on_public_header(self) -> None:
        source = (WEBSITE / "assets" / "auth-state-v2.js").read_text(encoding="utf-8")
        self.assertIn("function ensureHeaderGroup", source)
        self.assertIn("group.dataset.headerAuthActions = ''", source)
        self.assertIn("group.setAttribute('aria-label', 'Tài khoản StockRadar')", source)
        self.assertIn("header-account-tier", source)
        self.assertIn("header-account-upgrade", source)
        self.assertIn("isDedicatedAuthSurface", source)

    def test_login_default_redirect_is_site_home_not_today_or_account(self) -> None:
        source = (WEBSITE / "dang-nhap" / "index.html").read_text(encoding="utf-8")
        self.assertIn("url.searchParams.set('next', base.pathname || '/')", source)
        self.assertIn("Quay lại trang chủ StockRadar", source)
        self.assertNotIn("url.searchParams.set('next', 'hom-nay/')", source)

    def test_auth_state_asset_is_required_by_pages_build(self) -> None:
        source = (ROOT / "scripts" / "build_pages.py").read_text(encoding="utf-8")
        self.assertIn('AUTH_STATE_TAG = \'<script src="assets/auth-state-v2.js?v=20260905-auth8" defer></script>', source)
        self.assertIn('output / "assets" / "auth-state-v2.js"', source)


if __name__ == "__main__":
    unittest.main()
