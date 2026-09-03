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
        self.assertIn('"public-ux.js"', source)
        self.assertIn('"public-fallbacks-v4.js"', source)

    def test_built_homepage_uses_small_core_while_radar_keeps_full_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "pages"
            build_pages.build(output)
            for page in sorted(output.rglob("*.html")):
                inject_public_ux.inject_page(page, output)

            home = (output / "index.html").read_text(encoding="utf-8")
            radar = (output / "radar5" / "index.html").read_text(encoding="utf-8")

            for heavy in ("public-ux.js", "public-fallbacks-v4.js", "direct-ticker-nav-v1.js", "assets/app.js", "home-dashboard.css"):
                self.assertNotIn(heavy, home)
            self.assertIn("home-core-v1.js", home)
            for essential in ("public-copy-v7.js", "auth-production-gate.js", "mobile-touch-v1.css"):
                self.assertIn(essential, home)

            for full in ("assets/app.js", "public-ux.js", "public-fallbacks-v4.js", "direct-ticker-nav-v1.js"):
                self.assertIn(full, radar)


if __name__ == "__main__":
    unittest.main()