from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class AiRegistrationCtaTests(unittest.TestCase):
    def test_ai_chat_registration_ctas_use_current_plan_page(self):
        center = (ROOT / "website" / "assets" / "ai-center.js").read_text(encoding="utf-8")
        assistant = (ROOT / "website" / "assets" / "ai-assistant.js").read_text(encoding="utf-8")
        home = (ROOT / "website" / "index.html").read_text(encoding="utf-8")

        self.assertIn("dang-ky/?plan=free", center)
        self.assertIn("dang-ky/?plan=premium", center)
        self.assertIn("dang-ky/?plan=free", assistant)
        self.assertIn('href="dang-ky/?plan=free"', home)
        self.assertIn('href="dang-ky/?plan=premium"', home)

        self.assertNotIn("signup/?plan=free", center)
        self.assertNotIn("signup/?plan=free", assistant)
        self.assertNotIn('href="signup/?plan=free"', home)


if __name__ == "__main__":
    unittest.main()
