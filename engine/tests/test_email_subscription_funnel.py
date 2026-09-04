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

    def test_signup_auth_metadata_carries_legal_product_email_and_prefilled_lead(self):
        client = self.read("website/assets/signup-email-intent.js")
        for key in (
            "terms_accepted", "terms_version", "privacy_accepted", "privacy_version",
            "product_email_consent", "product_email_consent_version",
            "product_email_daily_brief", "product_email_event_alerts",
        ):
            self.assertIn(key, client)
        self.assertIn("params.get('email')", client)
        self.assertIn("form.elements.email.value = presetEmail", client)

    def test_account_exposes_free_daily_and_premium_alert_controls(self):
        account = self.read("website/tai-khoan/index.html")
        client = self.read("website/assets/email-preferences.js")
        self.assertIn("data-product-email-preferences", account)
        self.assertIn('name="daily_brief"', account)
        self.assertIn('name="event_alerts"', account)
        self.assertIn("assets/email-preferences.js", account)
        self.assertIn("product_email_preferences", client)
        self.assertIn("product_email_consent_events", client)
        self.assertIn("PREMIUM_TIERS", client)
        self.assertIn("profile.account_tier === 'FREE'", client)
        self.assertIn("master.disabled = !active", client)
        self.assertIn("Free · bản tin 09:00", client)
        self.assertIn("Cảnh báo mua/bán chỉ dành cho Premium", client)
        self.assertIn("alert_enabled", client)
        self.assertIn("data-watchlist-alert-toggle", client)

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
        self.assertIn("data-email-conversion", home)
        self.assertIn("data-home-email-form", home)
        self.assertIn('id="nhan-ban-tin"', home)
        self.assertIn('href="thanh-toan/?plan=premium"', home)
        self.assertIn("home-radar-sector-list", home)
        self.assertIn("home-tier-grid", home)
        self.assertIn("Free và Premium có gì?", home)
        self.assertIn("Nhận bản rà soát thị trường mỗi sáng", home)
        self.assertIn("FREE 09:00", home)
        self.assertIn("199K", home)
        for ticker in ("ACB", "VNM", "NKG", "CMG", "PVD", "FRT", "VHM", "POW", "GMD", "HAH"):
            self.assertIn(f"ticker={ticker}", home)
        for feature in (
            "Radar 30", "4M · CANSLIM · Payback", "So sánh theo ngành", "Hiệu quả khuyến nghị",
            "Định giá Bear / Base / Bull", "SEPA/VCP · Stage · Pivot",
            "VPA · RVOL · dòng tiền lớn", "Email & cảnh báo trong phiên",
        ):
            self.assertIn(feature, home)
        self.assertIn("30 mã", home)
        self.assertIn("10 ngành · 3 mã mỗi ngành", home)
        self.assertIn("4 mốc quét/ngày", home)
        self.assertIn("10:30 · 11:15 · 13:30 · 14:15", home)
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
        self.assertNotIn("Chưa có setup", home)
        self.assertNotIn("đang hoàn thiện", home.lower())
        self.assertNotIn("Trạng thái công khai", home)
        self.assertNotIn("Danh sách cổ phiếu đang theo dõi", home)
        self.assertNotIn("Chưa phát hành", home)
        self.assertNotIn("Chưa sẵn sàng", home)

    def test_email_lead_landing_captures_interest_then_routes_to_free_signup(self):
        page = self.read("website/nhan-ban-tin/index.html")
        client = self.read("website/assets/email-interest.js")
        self.assertIn('data-proposition="email-lead"', page)
        self.assertIn("Nhận bản rà soát 09:00 miễn phí", page)
        self.assertIn("data-email-interest-form", page)
        self.assertIn('name="daily_brief" type="checkbox"', page)
        self.assertIn('name="privacy" type="checkbox"', page)
        self.assertNotIn('name="daily_brief" type="checkbox" checked', page)
        self.assertIn('data-next-href="signup/?plan=free"', page)
        self.assertIn('href="thanh-toan/?plan=premium"', page)
        self.assertIn("renderNextStep", client)
        self.assertIn("data-email-interest-next", client)

    def test_radar_review_payload_is_30_tickers_10_sectors_3_each(self):
        payload = json.loads(self.read("website/public/data/ticker-universe.json"))
        items = payload["items"]
        counts = Counter(item["sector"] for item in items)
        self.assertEqual(len(items), 30)
        self.assertEqual(len(counts), 10)
        self.assertEqual(set(counts.values()), {3})
        self.assertTrue(all(item["exchange"] == "HOSE" for item in items))

    def test_registration_page_compares_free_daily_and_premium_intraday(self):
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
        self.assertIn("Có · bản cơ bản", register)
        self.assertIn("cảnh báo điểm mua/bán trong phiên", register.lower())
        self.assertIn("10:30 · 11:15 · 13:30 · 14:15", register)
        self.assertIn("data-email-interest-form", register)
        self.assertIn("assets/email-interest.js", register)

    def test_recommendation_page_uses_30_stock_radar_review_list(self):
        page = self.read("website/khuyen-nghi/index.html")
        self.assertIn("Tín hiệu hành động hiện tại", page)
        self.assertIn("0 mã", page)
        self.assertIn("Danh sách cổ phiếu theo Radar rà soát", page)
        self.assertIn("30 mã", page)
        for ticker in ("ACB", "VNM", "NKG", "HAH"):
            self.assertIn(f">{ticker}<", page)
        self.assertIn("không phải khuyến nghị mua", page)
        self.assertNotIn("Mã tham chiếu đang theo dõi", page)

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

    def test_public_interest_edge_has_origin_honeypot_and_rate_limit_contract(self):
        edge = self.read("supabase/functions/email-interest/index.ts")
        self.assertIn("ALLOWED_ORIGINS", edge)
        self.assertIn("payload.company", edge)
        self.assertIn("capture_email_subscription_interest", edge)
        self.assertIn("rate limit exceeded", edge)
        self.assertIn("SUPABASE_SERVICE_ROLE_KEY", edge)
        self.assertIn("PENDING_VERIFICATION", edge)
        self.assertIn("StockRadar chưa gửi báo cáo hoặc cảnh báo", edge)

    def test_privacy_page_discloses_pending_interest_retention(self):
        privacy = self.read("website/quyen-rieng-tu/index.html")
        self.assertIn("Đăng ký email trước khi xác minh tài khoản", privacy)
        self.assertIn("chờ xác minh", privacy)
        self.assertIn("tối đa 30 ngày", privacy)
        self.assertIn("không lưu địa chỉ IP thô", privacy)


if __name__ == "__main__":
    unittest.main()