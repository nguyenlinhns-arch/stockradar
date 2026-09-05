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
        self.assertIn(".card .value{", compact)
        self.assertIn("width:calc(100% - 16px)", compact)
        self.assertIn('content:"a  b /* not a comment */"', compact)
        self.assertIn('font-family:"Open Sans",sans-serif', compact)
        self.assertLess(len(compact.encode("utf-8")), len(source.encode("utf-8")))

    def test_comment_removal_matches_css_preprocessing_without_inventing_space(self):
        compact = minify_css(".a/**/.b { color: red; } .a /**/ .c { color: blue; }")
        self.assertIn(".a.b{color:red}", compact)
        self.assertIn(".a .c{color:blue}", compact)

    def test_custom_property_and_selector_significant_whitespace_are_preserved(self):
        source = '''
        :root { --gap:  10px; color: red; }
        .scope :hover { margin: calc(100% - 16px); }
        @media screen and (min-width: 600px) { .x { display: block; } }
        '''
        compact = minify_css(source)
        self.assertIn("--gap: 10px", compact)
        self.assertIn("color:red", compact)
        self.assertIn(".scope :hover{", compact)
        self.assertIn("calc(100% - 16px)", compact)
        self.assertIn("screen and (min-width:600px)", compact)

    def test_minifier_keeps_license_comment_and_escaped_quote(self):
        source = '/*! license */\n.x { content: "a\\\"  b"; color: red; }\n'
        compact = minify_css(source)
        self.assertIn("/*! license */", compact)
        self.assertIn('"a\\\"  b"', compact)
        self.assertIn("color:red", compact)

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
