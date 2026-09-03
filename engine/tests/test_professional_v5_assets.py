import tempfile
import unittest
from pathlib import Path

from scripts import build_pages, inject_public_ux


ROOT = Path(__file__).resolve().parents[2]


class ProfessionalV5AssetTests(unittest.TestCase):
    def test_professional_styles_cover_core_product_surfaces(self):
        css = (ROOT / "website" / "assets" / "professional-v5.css").read_text(encoding="utf-8")
        for marker in (
            "--panel-shadow",
            ".site-header",
            ".app-home .home-focus-panel",
            ".app-home .home-radar-tickers a",
            ".workspace-panel",
            ".radar-table",
            ".stock-report-shell",
            ".plan-card",
            ".auth-card",
            ".site-footer",
            "@media(max-width:760px)",
        ):
            self.assertIn(marker, css)

    def test_injector_loads_professional_styles_on_home_and_product_routes(self):
        injector = (ROOT / "scripts" / "inject_public_ux.py").read_text(encoding="utf-8")
        self.assertIn('"professional-v5.css"', injector)
        self.assertIn("20260904-pro5", injector)

        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "pages"
            build_pages.build(output)
            for page in sorted(output.rglob("*.html")):
                inject_public_ux.inject_page(page, output)

            for relative in ("index.html", "radar5/index.html", "dang-ky/index.html", "co-phieu/index.html"):
                source = (output / relative).read_text(encoding="utf-8")
                self.assertEqual(source.count("professional-v5.css"), 1, relative)


if __name__ == "__main__":
    unittest.main()
