from collections import Counter
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class EmailSubscriptionFunnelTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_signup_collects_premium_email_intent_without_prechecking(self):
        signup = self.read("website/signup/index.html")
        self.assertIn('name="email_daily_brief" type="checkbox"', signup)
        self.assertIn('name="email_event_alerts" type="checkbox"', signup)
        self.assertNotIn('name="email_daily_brief" type="checkbox" checked', signup)
        self.assertNotIn('name="email_event_alerts" type="checkbox" checked', signup)
        self.assertIn('name="selected_plan" value="free" checked', signup)
        self.assertIn('name="selected_plan" value="premium"', signup)
        self.assertIn("Free chỉ nhận email hệ thống", signup)
        self.assertIn("Báo cáo StockRadar lúc 09:00", signup)
        self.assertIn("Action Alert trong phiên", signup)
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

    def test_effective_product_email_entitlement_is_trial_or_paid_only(self):
        migration = self.read("supabase/migrations/20260904104050_enforce_paid_only_product_email.sql")
        lowered = migration.lower()
        self.assertIn("tier not in ('trial','paid')", lowered)
        self.assertIn("pref.daily_brief and prof.account_tier in ('trial','paid')", lowered)
        self.assertIn("pref.event_alerts and prof.account_tier in ('trial','paid')", lowered)
        self.assertIn("daily_brief_content_tier", lowered)
        self.assertIn("then 'premium'", lowered)
        self.assertNotIn("then 'free'", lowered)
        self.assertIn("eligible_for_premium", lowered)
        self.assertIn("create or replace function public.handle_email_verified()", lowered)
        self.assertIn("prof.account_tier in ('trial','paid')", lowered)

    def test_email_architecture_matches_paid_only_product_email(self):
        architecture = self.read("email/ARCHITECTURE.md")
        self.assertIn("**Free:** account/transactional email only", architecture)
        self.assertIn("**Trial/Paid:** may receive product email", architecture)
        self.assertIn("`DAILY_BRIEF` | Trial/Paid", architecture)
        self.assertIn("`EVENT_ALERT` | Trial/Paid", architecture)
        self.assertIn("09:00", architecture)
        self.assertIn("10:30", architecture)
        self.assertIn("11:15", architecture)
        self.assertIn("13:30", architecture)
        self.assertIn("14:15", architecture)
        self.assertIn("Free preferences can never become delivery entitlement", architecture)
        self.assertIn("verified email + explicit current consent", architecture)

    def test_homepage_source_still_routes_to_paid_conversion_and_public_lookup(self):
        home = self.read("website/index.html")
        self.assertIn("home-radar-sector-list", home)
        self.assertIn("data-live-radar-home", home)
        self.assertIn("home-tier-grid", home)
        self.assertIn("Free và Premium có gì?", home)
        self.assertIn("199K", home)
        for feature in (
            "Radar HOSE", "Full HOSE → Full-Scan Gate → Ranking", "So sánh theo ngành",
            "Hiệu quả khuyến nghị", "Market/Sector", "VPA/RVOL",
            "Email &amp; cảnh báo trong phiên",
        ):
            self.assertIn(feature, home)
        self.assertIn("4 mốc/ngày", home)
        self.assertIn("10:30 · 11:15 · 13:30 · 14:15", home)
        self.assertIn("Radar động theo snapshot", home)
        self.assertNotIn("Radar 30", home)
        self.assertNotIn("30 mã", home)
        self.assertNotIn("10 ngành · 3 mã", home)
        self.assertNotIn("co-phieu/?ticker=", home)
        self.assertIn("assets/home-focus-v1.css", home)
        self.assertIn("assets/home-conversion-v2.css", home)
        self.assertNotIn("assets/email-interest.js", home)
        self.assertNotIn("home-status-band", home)
        self.assertNotIn("home-status-grid", home)
        self.assertNotIn("assets/premium-preview-v7.css", home)
        self.assertNotIn("assets/home-dashboard.js", home)
        self.assertNotIn("home-watchlist-grid", home)
        self.assertNotIn("home-ticker-grid", home)
        self.assertNotIn("MẪU BÁO CÁO CHUYÊN SÂU", home)
        self.assertNotIn("MẪU EMAIL GÓI TRẢ PHÍ", home)
        self.assertNotIn("DỮ LIỆU MẪU", home)
        self.assertNotIn("MINH HỌA", home.upper())
        self.assertNotIn("đang hoàn thiện", home.lower())

    def test_home_and_global_conversion_state_skip_repeated_lead_cta(self):
        home_core = self.read("website/assets/home-core-v1.js")
        conversion_state = self.read("website/assets/conversion-state-v1.js")
        for source in (home_core, conversion_state):
            self.assertIn("sr_email_lead_captured", source)
            self.assertIn("emailDeliveryReady", source)
        self.assertIn("sr_pending_lead_email", home_core)
        self.assertIn("data-conversion-free-lead", conversion_state)

    def test_email_lead_landing_captures_premium_interest_then_routes_to_premium_signup(self):
        page = self.read("website/nhan-ban-tin/index.html")
        client = self.read("website/assets/email-interest.js")
        self.assertIn('data-proposition="email-lead"', page)
        self.assertIn("PREMIUM · EMAIL THEO WATCHLIST", page)
        self.assertIn("data-email-interest-form", page)
        self.assertIn('name="daily_brief" type="checkbox"', page)
        self.assertIn('name="event_alerts" type="checkbox"', page)
        self.assertIn('name="privacy" type="checkbox"', page)
        self.assertNotIn('name="daily_brief" type="checkbox" checked', page)
        self.assertNotIn('name="event_alerts" type="checkbox" checked', page)
        self.assertIn('data-next-href="signup/?plan=premium"', page)
        self.assertIn("Free chỉ nhận email hệ thống", page)
        self.assertIn("renderNextStep", client)
        self.assertIn("data-email-interest-next", client)
        self.assertIn("sr_pending_lead_email", client)
        self.assertIn("sessionStorage.setItem", client)
        self.assertNotIn("url.searchParams.set('email'", client)

    def test_email_lead_attribution_records_first_and_last_touch_without_public_access(self):
        migration = self.read("supabase/migrations/20260904004118_add_email_lead_attribution_v2.sql").lower()
        edge = self.read("supabase/functions/email-interest/index.ts")
        client = self.read("website/assets/email-interest.js")
        for marker in (
            "first_source_path", "last_source_path", "first_utm_source", "last_utm_source",
            "first_utm_campaign", "last_utm_campaign", "first_referrer_host", "last_referrer_host",
            "capture_email_subscription_interest_v2", "to service_role",
        ):
            self.assertIn(marker, migration)
        self.assertIn("capture_email_subscription_interest_v2", edge)
        for marker in ("source_path", "utm_source", "utm_campaign", "referrer_host"):
            self.assertIn(marker, edge)
            self.assertIn(marker, client)
        self.assertNotIn("service_role", client.lower())

    def test_reference_seed_is_non_publishable_and_pages_workflow_fail_closes_it(self):
        payload = json.loads(self.read("website/public/data/ticker-universe.json"))
        self.assertEqual(payload["data_status"], "BLOCKED_DATA_GATE")
        self.assertEqual(payload["public_scope"], "REFERENCE_ONLY")
        self.assertFalse(payload["full_universe"])
        self.assertEqual(payload["internal_reference"]["record_count"], 405)
        self.assertEqual(payload["internal_reference"]["validated_count"], 405)
        self.assertFalse(payload["internal_reference"]["raw_publication_allowed"])
        self.assertLess(len(payload["items"]), payload["internal_reference"]["record_count"])
        workflow = self.read(".github/workflows/pages.yml")
        self.assertIn("python scripts/fail_close_public_ticker_seed.py website/public/data/ticker-universe.json", workflow)
        self.assertLess(workflow.index("Run regression suite"), workflow.index("Fail-close public ticker seed before Pages build"))

    def test_registration_page_compares_free_public_and_premium_daily_intraday(self):
        register = self.read("website/dang-ky/index.html")
        self.assertIn('data-proposition="plans"', register)
        self.assertIn("data-plan-free", register)
        self.assertIn("data-plan-premium", register)
        self.assertIn("data-plan-comparison", register)
        self.assertIn('href="signup/?plan=free"', register)
        self.assertIn('href="signup/?plan=premium"', register)
        self.assertIn('href="thanh-toan/?plan=premium"', register)
        self.assertIn("StockRadar Free", register)
        self.assertIn("StockRadar Premium", register)
        self.assertIn("Free không nhận báo cáo 09:00", register)
        self.assertIn("Báo cáo email 09:00 hằng ngày</td><td class=\"plan-no\">Không", register)
        self.assertIn("báo cáo Premium 09:00 hằng ngày", register)
        self.assertNotIn("Có · bản cơ bản", register)
        self.assertIn("cảnh báo điểm mua/bán trong phiên", register.lower())
        self.assertIn("10:30 · 11:15 · 13:30 · 14:15", register)
        self.assertIn("data-email-interest-form", register)
        self.assertIn("assets/email-interest.js", register)

    def test_recommendation_page_uses_snapshot_bound_full_hose_radar(self):
        page = self.read("website/khuyen-nghi/index.html")
        self.assertIn("Tín hiệu hành động hiện tại", page)
        self.assertIn("0 mã", page)
        self.assertIn("Phạm vi quét", page)
        self.assertIn("Toàn HOSE", page)
        self.assertIn("Shortlist theo snapshot", page)
        self.assertIn("data-radar-review-list", page)
        self.assertIn("Không dùng mã mẫu hoặc danh sách lựa chọn thủ công", page)
        self.assertIn("Radar và Khuyến nghị là hai lớp khác nhau", page)
        self.assertNotIn("Radar 30", page)
        self.assertNotIn("10 ngành · 3 mã", page)
        for ticker in ("ACB", "MBB", "HPG", "FPT", "VHM"):
            self.assertNotIn(f">{ticker}<", page)

    def test_public_interest_client_calls_edge_without_privileged_secret(self):
        client = self.read("website/assets/email-interest.js")
        self.assertIn("/functions/v1/email-interest", client)
        self.assertIn("privacy_accepted", client)
        self.assertIn("consent_version", client)
        self.assertIn("payload.accepted !== true", client)
        self.assertIn("chờ xác minh", client)
        self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY", client)
        self.assertNotIn("service_role", client.lower())

    def test_pre_auth_interest_queue_never_authorizes_delivery(self):
        migration = self.read("supabase/migrations/20260903074211_add_public_email_subscription_interest_queue.sql").lower()
        self.assertIn("private.email_subscription_intents", migration)
        self.assertIn("pending_verification", migration)
        self.assertIn("interval '30 days'", migration)
        self.assertIn("revoke all on function public.capture_email_subscription_interest", migration)
        self.assertIn("grant execute on function public.capture_email_subscription_interest", migration)
        self.assertIn("to service_role", migration)
        self.assertIn("never authorizes delivery", migration)

    def test_public_interest_edge_has_origin_honeypot_rate_limit_and_v2_attribution(self):
        edge = self.read("supabase/functions/email-interest/index.ts")
        self.assertIn("ALLOWED_ORIGINS", edge)
        self.assertIn("payload.company", edge)
        self.assertIn("capture_email_subscription_interest_v2", edge)
        self.assertIn("rate limit exceeded", edge)
        self.assertIn("SUPABASE_SERVICE_ROLE_KEY", edge)
        self.assertIn("PENDING_VERIFICATION", edge)
        self.assertIn("stockradar-email-interest-v2", edge)

    def test_privacy_page_discloses_pending_interest_retention(self):
        privacy = self.read("website/quyen-rieng-tu/index.html")
        self.assertIn("Đăng ký email trước khi xác minh tài khoản", privacy)
        self.assertIn("chờ xác minh", privacy)
        self.assertIn("tối đa 30 ngày", privacy)
        self.assertIn("không lưu địa chỉ IP thô", privacy)


if __name__ == "__main__":
    unittest.main()
