from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class EmailSubscriptionFunnelTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_signup_collects_daily_and_premium_alert_intent_without_prechecking(self):
        signup = self.read("website/signup/index.html")
        self.assertIn('name="email_daily_brief" type="checkbox"', signup)
        self.assertIn('name="email_event_alerts" type="checkbox"', signup)
        self.assertNotIn('name="email_daily_brief" type="checkbox" checked', signup)
        self.assertNotIn('name="email_event_alerts" type="checkbox" checked', signup)
        self.assertIn("Premium", signup)
        self.assertIn("assets/signup-email-intent.js", signup)

    def test_signup_auth_metadata_carries_legal_and_product_email_consent(self):
        client = self.read("website/assets/signup-email-intent.js")
        for key in (
            "terms_accepted",
            "terms_version",
            "privacy_accepted",
            "privacy_version",
            "product_email_consent",
            "product_email_consent_version",
            "product_email_daily_brief",
            "product_email_event_alerts",
        ):
            self.assertIn(key, client)

    def test_account_exposes_tier_aware_email_center_and_ticker_alerts(self):
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
        self.assertIn("alert_enabled", client)
        self.assertIn("data-watchlist-alert-toggle", client)

    def test_signup_trigger_persists_preferences_and_consent_fail_closed(self):
        migration = self.read(
            "supabase/migrations/20260903064500_capture_signup_email_preferences_and_consent.sql"
        ).lower()
        self.assertIn("insert into public.product_email_preferences", migration)
        self.assertIn("insert into public.product_email_consent_events", migration)
        self.assertIn("'signup'", migration)
        self.assertIn("enabled,", migration)
        self.assertIn("false,", migration)
        self.assertIn("product_email_consent_version", migration)

    def test_free_daily_and_premium_alert_entitlement_are_separated_server_side(self):
        migration = self.read(
            "supabase/migrations/20260903071000_align_free_daily_and_premium_alert_interest.sql"
        )
        lowered = migration.lower()
        self.assertIn("free product email requires daily_brief enabled", lowered)
        self.assertIn("pref.event_alerts and prof.account_tier in ('trial','paid')", lowered)
        self.assertIn("eligible_for_premium", lowered)
        self.assertIn("create or replace function public.handle_email_verified()", lowered)
        self.assertIn("pref.daily_brief is true", lowered)
        self.assertIn("gate.current_consent_version", lowered)

    def test_email_architecture_matches_v214_free_and_premium_entitlement(self):
        architecture = self.read("email/ARCHITECTURE.md")
        self.assertIn("`daily` Free brief", architecture)
        self.assertIn("`state_change` / buy-sell event alerts: Trial/Paid only", architecture)
        self.assertIn("preference data, not delivery entitlement", architecture)
        self.assertNotIn("Free accounts are always suppressed for product content", architecture)
        self.assertIn("account signup remains fail-closed", architecture)

    def test_homepage_has_premium_previews_and_concrete_tickers(self):
        home = self.read("website/index.html")
        self.assertIn("data-email-conversion", home)
        self.assertIn('href="dang-ky/"', home)
        self.assertIn("home-ticker-grid", home)
        self.assertIn("<b>ACB</b>", home)
        self.assertIn("<b>VNM</b>", home)
        self.assertIn("Tín hiệu hành động hiện tại", home)
        self.assertIn("0 mã", home)
        self.assertIn("Danh sách cổ phiếu đang theo dõi", home)
        self.assertIn("16 mã", home)
        self.assertIn("MẪU BÁO CÁO CHUYÊN SÂU", home)
        self.assertIn("4M &amp; Payback Time", home)
        self.assertIn("Định giá Bear / Base / Bull", home)
        self.assertIn("MẪU EMAIL GÓI TRẢ PHÍ", home)
        self.assertIn("TOP 30 STOCKRADAR", home)
        self.assertIn("[StockRadar Premium] TOP 30 HOSE", home)
        self.assertIn("assets/premium-preview-v7.css", home)
        self.assertIn("assets/home-dashboard.js", home)
        self.assertNotIn("Mã tham chiếu đang theo dõi được tách khỏi khuyến nghị đã phát hành.", home)
        self.assertNotIn("DỮ LIỆU HOSE THAM CHIẾU", home)
        self.assertNotIn("Chưa phát hành", home)
        self.assertNotIn("Chưa sẵn sàng", home)

    def test_dedicated_registration_page_collects_interest_without_prechecking(self):
        register = self.read("website/dang-ky/index.html")
        self.assertIn("Đăng ký nhận bản tin chứng khoán mỗi ngày từ StockRadar.vn", register)
        self.assertIn("data-email-interest-form", register)
        self.assertIn('name="daily_brief" type="checkbox"', register)
        self.assertIn('name="event_alerts" type="checkbox"', register)
        self.assertNotIn('name="daily_brief" type="checkbox" checked', register)
        self.assertNotIn('name="event_alerts" type="checkbox" checked', register)
        self.assertIn("assets/email-interest.js", register)
        self.assertIn("assets/home-density.css", register)

    def test_recommendation_page_separates_published_recommendations_from_reference_tickers(self):
        page = self.read("website/khuyen-nghi/index.html")
        self.assertIn("Khuyến nghị đã phát hành", page)
        self.assertIn("0 mã", page)
        self.assertIn("Mã tham chiếu đang theo dõi", page)
        self.assertIn("16 mã", page)
        self.assertIn("ACB", page)
        self.assertIn("VNM", page)
        self.assertIn("không phải khuyến nghị mua", page)

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
        migration = self.read(
            "supabase/migrations/20260903074211_add_public_email_subscription_interest_queue.sql"
        ).lower()
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
