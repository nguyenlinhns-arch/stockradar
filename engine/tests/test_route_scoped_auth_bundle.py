import tempfile
import unittest
from pathlib import Path

from scripts import build_pages


class RouteScopedAuthBundleTests(unittest.TestCase):
    def test_auth_bundle_matches_route_capability(self):
        previous = build_pages.AUTH_ENABLED
        build_pages.AUTH_ENABLED = True
        try:
            with tempfile.TemporaryDirectory() as temp:
                output = Path(temp) / "site"
                (output / "co-phieu").mkdir(parents=True)
                (output / "signup").mkdir(parents=True)
                home_page = output / "index.html"
                stock_page = output / "co-phieu" / "index.html"
                signup_page = output / "signup" / "index.html"
                source = '<html><head></head><body></body></html>'

                home = build_pages.inject_auth_bundle(source, home_page, output)
                stock = build_pages.inject_auth_bundle(source, stock_page, output)
                signup = build_pages.inject_auth_bundle(source, signup_page, output)

                self.assertIn("assets/auth-config.js", home)
                self.assertNotIn("@supabase/supabase-js", home)
                self.assertNotIn("assets/auth.js", home)
                self.assertNotIn("assets/auth.css", home)

                self.assertIn("@supabase/supabase-js", stock)
                self.assertIn("assets/auth-config.js", stock)
                self.assertNotIn("assets/auth.js", stock)
                self.assertNotIn("assets/auth.css", stock)

                self.assertIn("@supabase/supabase-js", signup)
                self.assertIn("assets/auth-config.js", signup)
                self.assertIn("assets/auth.js", signup)
                self.assertIn("assets/auth-email-gate.js", signup)
                self.assertIn("assets/auth.css", signup)
        finally:
            build_pages.AUTH_ENABLED = previous

    def test_stock_route_is_the_only_public_premium_client_route(self):
        self.assertEqual(build_pages.PREMIUM_CLIENT_ROUTES, {"co-phieu"})
        self.assertIn("signup", build_pages.AUTH_ROUTES)
        self.assertIn("dang-nhap", build_pages.AUTH_ROUTES)
        self.assertIn("tai-khoan", build_pages.AUTH_ROUTES)


if __name__ == "__main__":
    unittest.main()
