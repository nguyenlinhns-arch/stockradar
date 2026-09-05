from pathlib import Path
import tempfile
import unittest

from scripts.optimize_home_asset_budget_v1 import minify_css, minify_home_css


class HomeCssMinificationTests(unittest.TestCase):
    def test_minifier_preserves_descendant_calc_and_strings(self):
        source = '''
        /* ordinary comment */
        .card   .value {
          width: calc(100% - 16px);
          content: "a  b /* not a comment */";
          font-family: "Open Sans", sans-serif;
        }
        '''
        compact = minify_css(source)
        self.assertNotIn("ordinary comment", compact)
        self.assertIn(".card .value", compact)
        self.assertIn("calc(100% - 16px)", compact)
        self.assertIn('"a  b /* not a comment */"', compact)
        self.assertIn('"Open Sans"', compact)
        self.assertLess(len(compact.encode("utf-8")), len(source.encode("utf-8")))

    def test_minifier_keeps_license_comment_and_escaped_quote(self):
        source = '/*! license */\n.x { content: "a\\\"  b"; color: red; }\n'
        compact = minify_css(source)
        self.assertIn("/*! license */", compact)
        self.assertIn('"a\\\"  b"', compact)

    def test_home_css_minification_only_rewrites_referenced_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            assets = output / "assets"
            assets.mkdir()
            referenced = assets / "home.css"
            untouched = assets / "other.css"
            referenced.write_text("/* remove */\n.a   .b {\n  color: red;\n}\n", encoding="utf-8")
            untouched.write_text("/* keep formatting */\n.x { color: blue; }\n", encoding="utf-8")
            before, after = minify_home_css(output, ["assets/home.css?v=1"])
            self.assertLess(after, before)
            self.assertNotIn("remove", referenced.read_text(encoding="utf-8"))
            self.assertIn("keep formatting", untouched.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
