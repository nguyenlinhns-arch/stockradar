from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PaidOnlyProductEmailContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_latest_entitlement_migration_requires_trial_or_paid(self):
        migration = self.read("supabase/migrations/20260904104050_enforce_paid_only_product_email.sql").lower()
        self.assertIn("tier not in ('trial','paid')", migration)
        self.assertIn("prof.account_tier in ('trial','paid')", migration)
        self.assertIn("daily_brief_content_tier", migration)
        self.assertIn("then 'premium'", migration)
        self.assertNotIn("then 'free'", migration)
        self.assertIn("update public.product_email_preferences", migration)
        self.assertIn("prof.account_tier not in ('trial','paid')", migration)

    def test_free_client_cannot_enable_product_email(self):
        client = self.read("website/assets/email-preferences.js")
        self.assertIn("const PREMIUM_TIERS = new Set(['TRIAL', 'PAID'])", client)
        self.assertIn("input.disabled = !premium", client)
        self.assertIn("master.disabled = !premium || !active", client)
        self.assertIn("button.disabled = !premium", client)
        self.assertIn("Free · chỉ email hệ thống", client)
        self.assertIn("Email nội dung StockRadar chỉ dành cho Trial/Premium", client)

    def test_free_signup_metadata_cannot_request_product_email(self):
        client = self.read("website/assets/signup-email-intent.js")
        self.assertIn("const premiumIntent = plan === 'premium'", client)
        self.assertIn("premiumIntent && form.elements.email_daily_brief?.checked", client)
        self.assertIn("premiumIntent && form.elements.email_event_alerts?.checked", client)
        self.assertIn("input.disabled = !premium", client)
        self.assertIn("if (!premium) input.checked = false", client)
        self.assertIn("Free có phí 0đ", client)
        self.assertIn("email hệ thống cần thiết cho tài khoản", client)

    def test_plan_page_does_not_sell_daily_email_as_free(self):
        plans = self.read("website/dang-ky/index.html")
        self.assertIn("Free không nhận báo cáo 09:00", plans)
        self.assertIn("Báo cáo email 09:00 hằng ngày</td><td class=\"plan-no\">Không", plans)
        self.assertIn("báo cáo Premium 09:00 hằng ngày", plans)
        self.assertNotIn("Có · bản cơ bản", plans)
        self.assertNotIn("Free: bản rà soát 09:00", plans)

    def test_pages_transform_corrects_legacy_signup_copy_before_publish(self):
        transformer = self.read("scripts/apply_premium_email_product_v1.py")
        self.assertIn("Free để tra cứu.<br>Premium để nhận lớp quyết định.", transformer)
        self.assertIn("Email Premium StockRadar", transformer)
        self.assertIn("Hai lựa chọn này chỉ dành cho Trial/Paid", transformer)
        self.assertIn("assets/signup-email-intent.js?v=20260904-paid2", transformer)
        self.assertIn("FREE + PREMIUM", transformer)
        self.assertIn("PREMIUM", transformer)


if __name__ == "__main__":
    unittest.main()
