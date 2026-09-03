import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class MobileTouchAccessibilityTests(unittest.TestCase):
    def test_mobile_touch_css_uses_large_targets_and_focus_visible(self):
        source = (ROOT / "website" / "assets" / "mobile-touch-v1.css").read_text(encoding="utf-8")
        self.assertIn("@media(max-width:760px)", source)
        self.assertIn("min-height:44px", source)
        self.assertIn(".home-radar-tickers a", source)
        self.assertIn(":focus-visible", source)
        self.assertIn("prefers-reduced-motion:reduce", source)

    def test_pages_injector_loads_mobile_touch_css(self):
        source = (ROOT / "scripts" / "inject_public_ux.py").read_text(encoding="utf-8")
        self.assertIn('"mobile-touch-v1.css"', source)
        self.assertIn("mobile_css", source)
        self.assertIn("20260903-touch1", source)


if __name__ == "__main__":
    unittest.main()
