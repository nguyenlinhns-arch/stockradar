from collections import Counter
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class EmailSubscriptionFunnelTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_signup_collects_free_daily_and_premium_alert_intent_without_prechecking(self):
        signup = self.read("website/signup/index.html")
        self.assertIn('name="email_daily_brief" type="checkbox"', signup)
        self.assertIn('name="email_event_alerts" type="checkbox"', signup)
        self.assertNotIn('name="email_daily_brief" type="checkbox" checked', signup)
        self.assertNotIn('name="email_event_alerts" type="checkbox" checked', signup)
        self.assertIn('name="selected_plan" value="free" checked', signup)
        self.assertIn('name="selected_plan" value="premium"', signup)
        self.assertIn("bản rà soát thị trường lúc 09:00 mỗi ngày", signup)
        self.assertIn("cảnh báo điểm mua/bán trong phiên", signup)
        self.assertIn("FREE + PREMIUM", signup)
        self.assertIn("PREMIUM", signup)
        self.assertIn("assets/signup-email-intent.js", signup)

    def test_signup_auth_metadata_and_session_prefill_avoid_url_pii(self):
        client = self.read("website/assets/signup-email-intent.js")
        for key in (
            "terms_accepted", "terms_version", "privacy_accepted", "privacy_version",
            "product_email_consent", "product_email_consent_version",
            "product_email_daily_brief", "product_email_event_alerts",
        ):
            self.assertIn(key, client)
        self.assertIn("sr_pending_lead_email", client)
        self.assertIn("pendingLeadEmail()", client)
        self.assertIn("form.elements.email.value = presetEmail", client)
        self.assertIn("params.delete('email')", client)
        self.assertIn("window.history.replaceState", client)
        self.assertIn("clearPendingLeadEmail()", client)

    def test_account_exposes_premium_email_and_per_ticker_alert_controls(self):
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

    def test_signup_trigger_persists_preferences_and_consent_fail_closed(self):
        migration = self.read("supabase/migrations/20260903064500_capture_signup_email_preferences_and_consent.sql").lower()
        self.assertIn("insert into public.product_email_preferences", migration)
        self.assertIn("insert into public.product_email_consent_events", migration)
        self.assertIn("'signup'", migration)
        self.assertIn("enabled,", migration)
        self.assertIn("false,", migration)
        self.assertIn("product_email_consent_version", migration)

    def test_product_email_entitlement_allows_free_daily_but_masks_premium_alerts(self):
        migration = self.read("supabase/migrations/20260904060000_restore_free_daily_premium_intraday_email.sql")
        lowered = migration.lower()
        self.assertIn("tier = 'free' and not coalesce(new.daily_brief, false)", lowered)
        self.assertIn("pref.daily_brief and prof.account_tier in ('free','trial','paid')", lowered)
        self.assertIn("pref.event_alerts and prof.account_tier in ('trial','paid')", lowered)
        self.assertIn("daily_brief_content_tier", lowered)
        self.assertIn("then 'free'", lowered)
        self.assertIn("eligible_for_premium", lowered)
        self.assertIn("create or replace function public.handle_email_verified()", lowered)
        self.assertIn("prof.account_tier = 'free' and pref.daily_brief is true", lowered)

    def test_email_architecture_matches_free_daily_and_premium_alert_split(self):
        architecture = self.read("email/ARCHITECTURE.md")
        self.assertIn("`daily`: Free/Trial/Paid", architecture)
        self.assertIn("`state_change` / buy-sell event alerts: Trial/Paid only", architecture)
        self.assertIn("09:00 Vietnam time", architecture)
        self.assertIn("10:30 / 11:15 / 13:30 / 14:15", architecture)
        self.assertIn("Preference data is not delivery entitlement", architecture)
        self.assertIn("account signup remains fail-closed", architecture)

    def test_homepage_is_email_first_with_clear_paid_conversion(self):
        home = self.read("website/index.html")
        self.assertIn("StockRadar", home)

    def test_email_lead_landing_captures_interest_then_routes_to_free_signup(self):
        page = self.read("website/nhan-ban-tin/index.html")
        self.assertIn("data-email-interest-form", page)

    def test_pre_auth_interest_queue_never_authorizes_delivery(self):
        migration = self.read("supabase/migrations/20260903074211_add_public_email_subscription_interest_queue.sql").lower()
        self.assertIn("pending", migration)

    def test_public_interest_client_calls_edge_without_privileged_secret(self):
        source = self.read("website/assets/email-interest.js")
        self.assertNotIn("service_role", source.lower())

    def test_reference_seed_is_non_publishable_and_pages_workflow_fail_closes_it(self):
        workflow = self.read(".github/workflows/pages.yml")
        self.assertIn("fail_close_public_ticker_seed.py", workflow)

    def test_registration_page_compares_free_daily_and_premium_intraday(self):
        page = self.read("website/signup/index.html")
        self.assertIn("FREE + PREMIUM", page)

    def test_recommendation_page_uses_snapshot_bound_full_hose_radar(self):
        page = self.read("website/khuyen-nghi/index.html")
        self.assertNotIn("Radar 30", page)

    def test_email_lead_attribution_records_first_and_last_touch_without_public_access(self):
        migration = self.read("supabase/migrations/20260904004118_add_email_lead_attribution_v2.sql").lower()
        self.assertIn("first", migration)
        self.assertIn("last", migration)

    def test_public_interest_edge_has_origin_honeypot_rate_limit_and_v2_attribution(self):
        source = self.read("supabase/functions/email-interest/index.ts")
        self.assertIn("ALLOWED_ORIGINS", source)

    def test_signup_trigger_persists_preferences_and_consent_fail_closed(self):
        migration = self.read("supabase/migrations/20260903064500_capture_signup_email_preferences_and_consent.sql").lower()
        self.assertIn("insert into public.product_email_preferences", migration)
        self.assertIn("insert into public.product_email_consent_events", migration)

    def test_home_and_global_conversion_state_skip_repeated_lead_cta(self):
        source = self.read("website/assets/conversion-state-v1.js")
        self.assertIn("sr_email_lead_captured", source)

    def test_privacy_page_discloses_pending_interest_retention(self):
        page = self.read("website/quyen-rieng-tu/index.html")
        self.assertIn("2026-09-04", page)


if __name__ == "__main__":
    unittest.main()
