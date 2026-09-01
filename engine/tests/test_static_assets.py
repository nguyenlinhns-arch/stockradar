import struct
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

from scripts import build_pages


ROOT = Path(__file__).resolve().parents[2]
WEBSITE = ROOT / "website"
class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references: list[str] = []
        self.base_href: str | None = None
        self.has_title = False
        self.has_description = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "title":
            self.has_title = True
        if tag == "meta" and values.get("name") == "description" and values.get("content"):
            self.has_description = True
        if tag == "base" and values.get("href"):
            self.base_href = values["href"]
        for key in (() if tag == "base" else ("href", "src")):
            if values.get(key):
                self.references.append(values[key])


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        if handle.read(8) != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"Not a PNG: {path}")
        length = struct.unpack(">I", handle.read(4))[0]
        chunk = handle.read(4)
        if chunk != b"IHDR" or length < 8:
            raise ValueError(f"Missing PNG IHDR: {path}")
        return struct.unpack(">II", handle.read(8))


class StaticAssetTests(unittest.TestCase):
    def test_html_pages_have_metadata_and_valid_internal_assets(self) -> None:
        for html in WEBSITE.rglob("index.html"):
            parser = AssetParser()
            parser.feed(html.read_text(encoding="utf-8"))
            self.assertTrue(parser.has_title, html)
            self.assertTrue(parser.has_description, html)
            for ref in parser.references:
                if urlparse(ref).scheme or ref.startswith(("mailto:", "tel:", "#")):
                    continue
                base_url = urljoin(html.as_uri(), parser.base_href or "")
                parsed = urlparse(urljoin(base_url, ref))
                path = Path(unquote(parsed.path))
                if parsed.path.endswith("/") or path.is_dir():
                    path /= "index.html"
                self.assertTrue(path.is_file(), f"{html}: missing {ref} -> {path}")

    def test_pages_build_is_static_and_truthful(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "pages"
            build_pages.build(output)
            self.assertTrue((output / ".nojekyll").is_file())
            self.assertFalse((output / "server.py").exists())
            for html in output.rglob("*.html"):
                source = html.read_text(encoding="utf-8")
                self.assertIn('data-api-mode="disabled"', source, html)
                self.assertIn('name="robots" content="noindex,nofollow"', source, html)

    def test_github_pages_workflow_runs_tests_before_deploy(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
        self.assertIn("python -m unittest discover -s engine/tests -v", workflow)
        self.assertIn("python scripts/build_pages.py --output .pages-site", workflow)
        self.assertLess(workflow.index("Run regression suite"), workflow.index("Deploy to GitHub Pages"))

    def test_public_pages_do_not_use_old_personal_brand(self) -> None:
        for path in list(WEBSITE.rglob("*.html")) + list(WEBSITE.rglob("*.js")) + list(WEBSITE.rglob("*.css")):
            self.assertNotIn("Linh", path.read_text(encoding="utf-8"), path)

    def test_six_creatives_have_feed_and_reels_variants(self) -> None:
        output = ROOT / "growth" / "creatives" / "output"
        feed = sorted(output.glob("*_feed_4x5.png"))
        reels = sorted(output.glob("*_reels_9x16.png"))
        self.assertEqual(len(feed), 6)
        self.assertEqual(len(reels), 6)
        self.assertTrue(all(png_dimensions(path) == (1080, 1350) for path in feed))
        self.assertTrue(all(png_dimensions(path) == (1080, 1920) for path in reels))


if __name__ == "__main__":
    unittest.main()
