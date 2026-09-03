import tempfile
import unittest
from pathlib import Path

from scripts import build_pages, inject_public_ux


ROOT = Path(__file__).resolve().parents[2]


class HomepageAssetBudgetTests(unittest.TestCase):
    def test_injector_replaces_legacy_home_runtime(self):
        source = (ROOT / "scripts" / "inject_public_ux.py").read_text(encoding="utf-8")
        self.assertIn("def is_homepage", source)
        self.assertIn("def optimize_homepage_assets", source)
        self.assertIn("home-dashboard\\.css", source)
        self.assertIn("assets/app\\.js", source)
        self.assertIn('"home-core-v1.js"', source)
        self.assertIn("if is_homepage(page, output):", source)

    def test_home_core_owns_navigation_search_and_registration_readiness(self):
        source = (ROOT / "website" / "assets" / "home-core-v1.js").read_text(encoding="utf-8")
        for marker in (
            "site-v4", "mountNavigation", "mountTickerSearch", "mountRegistration",
            "emailDeliveryReady", "registrationUrl", "signup/", "dang-ky/", "window.location.assign",
        ):
            self.assertIn(marker, source)

    def test_built_homepage_is_self_contained_while_radar_keeps_full_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "pages"
            build_pages.build(output)
            for page in sorted(output.rglob("*.html")):
                inject_public_ux.inject_page(page, output)

            home = (output / "index.html").read_text(encoding="utf-8")
            radar = (output / "radar5" / "index.html").read_text(encoding="utf-8")

            for heavy in (
                "public-ux.css", "public-ux.js", "public-fallbacks-v4.js", "direct-ticker-nav-v1.js",
                "auth-production-gate.js", "header-auth-dedupe-v6.js", "public-copy-v7.js",
                "assets/app.js", "home-dashboard.css",
            ):
                self.assertNotIn(heavy, home)
            for essential in ("home-core-v1.js", "site-v4.css", "mobile-touch-v1.css"):
                self.assertIn(essential, home)

            for full in (
                "assets/app.js", "public-ux.css", "public-ux.js", "public-fallbacks-v4.js",
                "direct-ticker-nav-v1.js", "auth-production-gate.js", "header-auth-dedupe-v6.js", "public-copy-v7.js",
            ):
                self.assertIn(full, radar)


if __name__ == "__main__":
    unittest.main()