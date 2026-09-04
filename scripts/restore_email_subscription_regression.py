from pathlib import Path
import re
import subprocess

BASE = "731133fd7bfd9e08598ae3d4ffce88c738b192e5"
TEST = Path("engine/tests/test_email_subscription_funnel.py")
WORKFLOW = Path(".github/workflows/restore-email-subscription-test.yml")

subprocess.run(["git", "checkout", BASE, "--", str(TEST)], check=True)
text = TEST.read_text(encoding="utf-8")
pattern = re.compile(
    r"    def test_account_exposes_free_daily_and_premium_alert_controls\(self\):\n.*?(?=    def test_signup_trigger_persists_preferences_and_consent_fail_closed)",
    re.S,
)
replacement = '''    def test_account_exposes_premium_email_and_per_ticker_alert_controls(self):
        account = self.read("website/tai-khoan/index.html")
        email_client = self.read("website/assets/email-preferences.js")
        watch_client = self.read("website/assets/account-preferences.js")
        self.assertIn("data-product-email-preferences", account)
        self.assertIn('name="daily_brief"', account)
        self.assertIn('name="event_alerts"', account)
        self.assertIn("assets/email-preferences.js", account)
        self.assertIn("product_email_preferences", email_client)
        self.assertIn("product_email_consent_events", email_client)
        self.assertIn("PREMIUM_TIERS", email_client)
        self.assertIn("const premium = isPremiumTier(profile.account_tier);", email_client)
        self.assertIn("master.disabled = !premium || !active", email_client)
        self.assertIn("Free · chỉ email hệ thống", email_client)
        self.assertIn("Báo cáo hằng ngày và cảnh báo hành động được mở ở Trial/Premium", email_client)
        self.assertIn("alert_enabled", watch_client)
        self.assertIn("data-watchlist-alert", watch_client)
        self.assertIn("Cảnh báo theo từng mã chỉ dành cho Trial/Premium", watch_client)

'''
text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise SystemExit("Could not replace account email regression method")
TEST.write_text(text, encoding="utf-8")
if WORKFLOW.exists():
    WORKFLOW.unlink()
