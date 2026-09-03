import tempfile
import unittest
from pathlib import Path

from scripts import build_pages, inject_public_ux


ROOT = Path(__file__).resolve().parents[2]


class HomepageAssetBudgetTests(unittest.TestCase):
    def test_injector_skips_heavy_data_patch_scripts_only_on_homepage(self):
        source = (ROOT / "scripts" / "inject_public_ux.py").read_text(encoding="utf-8")
        self.assertIn("def is_homepage", source)
        self.assertIn("if not is_homepage(page, output):", source)
        self.assertIn('"public-ux.js"', source)
        self.assertIn('"public-fallbacks-v4.js"', source)

    def test_built_homepage_omits_data_patch_scripts_but_radar_keeps_them(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "pages"
            build_pages.build(output)
            inject_public_ux.main = inject_public_ux.main  # keep import explicit for static analyzers
            for page in sorted(output.rglob("*.html")):
                inject_public_ux.inject_page(page, output)

            home = (output / "index.html").read_text(encoding="utf-8")
            radar = (output / "radar5" / "index.html").read_text(encoding="utf-8")
            for heavy in ("public-ux.js", "public-fallbacks-v4.js"):
                self.assertNotIn(heavy, home)
                self.assertIn(heavy, radar)
            for essential in ("public-copy-v7.js", "direct-ticker-nav-v1.js", "auth-production-gate.js", "mobile-touch-v1.css"):
                self.assertIn(essential, home)


if __name__ == "__main__":
    unittest.main()
