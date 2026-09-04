from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class AiRegistrationCtaTests(unittest.TestCase):
    def test_ai_chat_registration_and_upgrade_ctas_follow_account_state(self):
        center = (ROOT / "website" / "assets" / "ai-center.js").read_text(encoding="utf-8")
        assistant = (ROOT / "website" / "assets" / "ai-assistant.js").read_text(encoding="utf-8")
        home = (ROOT / "website" / "index.html").read_text(encoding="utf-8")

        # Guest -> Free remains a registration action.
        self.assertIn("dang-ky/?plan=free", center)
        self.assertIn("dang-ky/?plan=free", assistant)
        self.assertIn('href="dang-ky/?plan=free"', home)

        # Signed-in Free -> Premium is an upgrade/payment action, never another signup.
        self.assertIn("thanh-toan/?plan=premium", center)
        self.assertIn("Nâng Premium", center)
        self.assertNotIn("dang-ky/?plan=premium", center)

        # The public plan card may still begin a direct Premium registration flow for guests.
        self.assertIn('href="dang-ky/?plan=premium"', home)

        self.assertNotIn("signup/?plan=free", center)
        self.assertNotIn("signup/?plan=free", assistant)
        self.assertNotIn('href="signup/?plan=free"', home)


if __name__ == "__main__":
    unittest.main()
