import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ConversionFunnelAssetTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_global_conversion_rail_is_ai_free_first_and_state_aware(self):
        injector = self.read("scripts/inject_public_ux.py")
        state = self.read("website/assets/conversion-state-v1.js")
        for route in ("radar5", "kiem-tra-co-phieu", "khuyen-nghi", "hieu-qua", "nganh", "co-phieu"):
            self.assertIn(f'"{route}"', injector)
        self.assertNotIn('"phan-tich",', injector)
        self.assertIn("Bắt đầu với StockRadar AI Free 10 câu/ngày", injector)
        self.assertIn("Premium đang tạm dừng kích hoạt mới", injector)
        self.assertIn("checkout_ready()", injector)
        self.assertIn("data-conversion-free-lead", injector)
        self.assertIn("data-conversion-mobile-lead", injector)
        self.assertIn("conversion-state-v1.js", injector)
        self.assertIn("sr_email_lead_captured", state)
        self.assertIn("Hoàn tất tài khoản Free", state)
        self.assertIn("thanh-toan", injector)

    def test_only_free_account_center_gets_contextual_premium_upsell(self):
        client = self.read("website/assets/account-upgrade-v1.js")
        styles = self.read("website/assets/account-upgrade-v1.css")
        injector = self.read("scripts/inject_public_ux.py")

        # Trial/Paid/Premium are all normalized to the buyer-facing Premium state.
        for marker in (
            "normalized === 'PAID'",
            "normalized === 'TRIAL'",
            "normalized === 'PREMIUM'",
            "return 'PREMIUM'",
            "normalized === 'FREE'",
            "return 'FREE'",
        ):
            self.assertIn(marker, client)
        self.assertIn("if (tier !== 'FREE')", client)
        self.assertIn("card.hidden = true", client)
        self.assertIn("data-account-tier", client)
        self.assertIn("199.000đ", client)
        self.assertIn("thanh-toan/?plan=premium", client)
        self.assertIn("Buy Zone · Stop · Target · R/R", client)
        self.assertIn("10:30 · 11:15 · 13:30 · 14:15", client)
        self.assertIn("account-upgrade-v1.css", injector)
        self.assertIn("account-upgrade-v1.js", injector)
        self.assertIn("@media(max-width:680px)", styles)

    def test_lead_capture_uses_private_session_prefill_and_campaign_attribution(self):
        lead = self.read("website/assets/email-interest.js")
        home = self.read("website/assets/home-core-v1.js")
        signup = self.read("website/assets/signup-email-intent.js")
        for source in (lead, home):
            self.assertIn("sr_pending_lead_email", source)
            self.assertIn("utm_source", source)
            self.assertIn("utm_campaign", source)
            self.assertIn("referrer_host", source)
            self.assertIn("source_path", source)
        self.assertIn("sessionStorage.getItem(PENDING_LEAD_EMAIL_KEY)", signup)
        self.assertIn("params.delete('email')", signup)
        self.assertNotIn("searchParams.set('email'", lead)
        self.assertNotIn("searchParams.set('email'", home)


if __name__ == "__main__":
    unittest.main()
