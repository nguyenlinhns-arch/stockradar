from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PaidOnlyEmailRuntimeTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_signup_and_interest_page_never_promise_free_product_email(self) -> None:
        signup = self.read("website/signup/index.html")
        lead = self.read("website/nhan-ban-tin/index.html")
        for source in (signup, lead):
            self.assertIn("Free chỉ nhận email hệ thống", source)
            self.assertNotIn("FREE + PREMIUM", source)
            self.assertNotIn("Free nhận bản tin 09:00", source)
            self.assertNotIn("Nhận bản rà soát 09:00 miễn phí", source)
        self.assertIn('data-next-href="signup/?plan=premium"', lead)

    def test_paid_only_migration_is_authoritative_and_masks_all_product_email_for_free(self) -> None:
        sql = self.read("supabase/migrations/20260904110500_assert_paid_only_product_email.sql").lower()
        for marker in (
            "account_tier not in ('trial','paid')",
            "premium product email requires trial or paid",
            "pref.daily_brief and prof.account_tier in ('trial','paid')",
            "pref.event_alerts and prof.account_tier in ('trial','paid')",
            "pref.post_session_digest and prof.account_tier in ('trial','paid')",
            "pref.weekly_report and prof.account_tier in ('trial','paid')",
            "daily_brief_content_tier",
            "then 'premium'",
            "eligible_for_premium",
        ):
            self.assertIn(marker, sql)
        self.assertNotIn("then 'free'", sql)

    def test_email_interest_is_pending_interest_not_delivery_entitlement(self) -> None:
        client = self.read("website/assets/email-interest.js")
        edge = self.read("supabase/functions/email-interest/index.ts")
        self.assertIn("PENDING_VERIFICATION", edge)
        self.assertIn("PREMIUM_EMAIL_INTEREST", edge)
        self.assertIn("chưa tạo quyền nhận email", edge)
        self.assertIn("chưa phải quyền gửi email", client)
        self.assertIn("signup/?plan=premium", client)
        self.assertNotIn("Hoàn tất tạo tài khoản Free", client)

    def test_runtime_readiness_is_private_blocker_based_and_secret_free(self) -> None:
        sql = self.read("supabase/migrations/20260904111000_add_email_runtime_readiness.sql")
        for marker in (
            "get_stockradar_email_runtime_readiness_v1",
            "PROVIDER_NOT_SELECTED",
            "PROVIDER_CONFIG_APPROVAL_MISSING",
            "SENDER_DOMAIN_APPROVAL_MISSING",
            "UNSUBSCRIBE_APPROVAL_MISSING",
            "BOUNCE_COMPLAINT_APPROVAL_MISSING",
            "COMPLIANCE_APPROVAL_MISSING",
            "SCHEDULER_NOT_CONFIGURED",
            "CRON_NOT_ACTIVE",
            "STALE_PROCESSING_OUTBOX",
            "ready_to_activate",
            "ready_to_send_now",
            "grant execute on function public.get_stockradar_email_runtime_readiness_v1() to service_role",
        ):
            self.assertIn(marker, sql)
        for secret_marker in ("RESEND_API_KEY", "SUPABASE_SERVICE_ROLE_KEY", "whsec_", "sb_secret_"):
            self.assertNotIn(secret_marker, sql)

    def test_activation_runbook_never_allows_placeholder_evidence_or_fake_stock_signal(self) -> None:
        runbook = self.read("email/PRODUCTION_ACTIVATION.md")
        for marker in (
            "Free receives only necessary account/transactional email",
            "ready_to_activate = false",
            "RESEND_API_KEY",
            "SENDER_DOMAIN",
            "UNSUBSCRIBE",
            "BOUNCE_COMPLAINT",
            "COMPLIANCE",
            "Never create placeholder or guessed approvals",
            "Never generate a fake BUY/SELL",
            "activate_stockradar_email_delivery_v1",
            "deactivate_stockradar_email_delivery_v1",
        ):
            self.assertIn(marker, runbook)

    def test_architecture_and_runbook_point_to_same_paid_only_source_of_truth(self) -> None:
        architecture = self.read("email/ARCHITECTURE.md")
        runbook = self.read("email/PRODUCTION_ACTIVATION.md")
        marker = "20260904110500_assert_paid_only_product_email.sql"
        self.assertIn(marker, architecture)
        self.assertIn("Trial/Paid", architecture)
        self.assertIn("Free:", architecture)
        self.assertIn("Free receives only necessary account/transactional email", runbook)


if __name__ == "__main__":
    unittest.main()
