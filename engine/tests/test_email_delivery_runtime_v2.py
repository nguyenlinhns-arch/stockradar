from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class EmailDeliveryRuntimeV2Tests(unittest.TestCase):
    def read(self, path: str) -> str:
        return (ROOT / path).read_text(encoding="utf-8")

    def test_migration_adds_ttl_idempotent_claim_audit_and_unsubscribe(self) -> None:
        sql = self.read("supabase/migrations/20260904101500_add_email_delivery_runtime_v2.sql")
        for marker in (
            "expires_at timestamptz",
            "email_delivery_events",
            "email_unsubscribe_tokens",
            "enqueue_stockradar_email_v2",
            "claim_stockradar_email_outbox_v1",
            "for update of o skip locked",
            "issue_stockradar_unsubscribe_token_v1",
            "apply_stockradar_unsubscribe_v1",
            "record_stockradar_email_delivery_event_v1",
            "DELIVERY_GATE_CLOSED",
            "EXPIRED_BEFORE_SEND",
            "MAX_ATTEMPTS",
            "event alert requires material state change",
        ):
            self.assertIn(marker, sql)
        self.assertIn("to service_role", sql)
        self.assertNotIn("grant execute on function public.claim_stockradar_email_outbox_v1(integer) to authenticated", sql)

    def test_worker_requires_internal_service_auth_and_provider_is_fail_closed(self) -> None:
        source = self.read("supabase/functions/email-worker/index.ts")
        for marker in (
            'req.headers.get("authorization") === `Bearer ${service}`',
            'req.headers.get("x-stockradar-scheduler")',
            "verify_stockradar_email_scheduler_token_v1",
            "sha256Hex(schedulerToken)",
            'return valid === true',
            "PROVIDER_NOT_CONFIGURED",
            "RESEND_API_KEY",
            "STOCKRADAR_EMAIL_FROM",
            "claim_stockradar_email_outbox_v1",
            "preflight_stockradar_email_outbox_v1",
            "finish_stockradar_email_outbox_v1",
            '"Idempotency-Key":idem',
            '"List-Unsubscribe"',
            '"List-Unsubscribe-Post":"List-Unsubscribe=One-Click"',
            "STOCKRADAR_FUNCTIONS_BASE_URL",
            "XEM TRẠNG THÁI MỚI NHẤT",
            "Không có thay đổi hành động mới",
            "suppressed",
        ):
            self.assertIn(marker, source)
        self.assertNotIn("re_xxxxxxxxx", source)
        self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY =", source)
        self.assertLess(source.index("authorizedServiceRequest"), source.index("PROVIDER_NOT_CONFIGURED"))
        self.assertLess(
            source.index("preflight_stockradar_email_outbox_v1"),
            source.index("issue_stockradar_unsubscribe_token_v1"),
        )
        self.assertLess(
            source.index("preflight_stockradar_email_outbox_v1"),
            source.index("fetch(RESEND_ENDPOINT"),
        )

    def test_final_preflight_rechecks_ttl_consent_suppression_and_delivery_gate(self) -> None:
        sql = self.read("supabase/migrations/20260904103000_add_email_send_preflight.sql")
        for marker in (
            "preflight_stockradar_email_outbox_v1",
            "OUTBOX_NOT_PROCESSING",
            "EXPIRED_AT_PREFLIGHT",
            "EMAIL_NOT_VERIFIED_AT_PREFLIGHT",
            "NO_EMAIL_PREFERENCE_AT_PREFLIGHT",
            "SUPPRESSED_AT_PREFLIGHT_",
            "DELIVERY_DISABLED_AT_PREFLIGHT",
            "CONSENT_REVOKED_AT_PREFLIGHT",
            "ENTITLEMENT_CHANGED_AT_PREFLIGHT",
            "eligible_for_premium",
            "status='SUPPRESSED'",
            "to service_role",
        ):
            self.assertIn(marker, sql)
        self.assertNotIn(
            "grant execute on function public.preflight_stockradar_email_outbox_v1(uuid) to authenticated",
            sql,
        )

    def test_webhook_verifies_raw_svix_signature_and_replay_window(self) -> None:
        source = self.read("supabase/functions/email-webhook/index.ts")
        for marker in (
            "await req.text()",
            'headers.get("svix-id")',
            'headers.get("svix-timestamp")',
            'headers.get("svix-signature")',
            'secret.startsWith("whsec_")',
            'Math.abs(Math.floor(Date.now() / 1000) - timestampNumber) > 300',
            'name: "HMAC", hash: "SHA-256"',
            "record_stockradar_email_delivery_event_v1",
            '"email.bounced"',
            '"email.complained"',
            "RESEND_WEBHOOK_SECRET",
        ):
            self.assertIn(marker, source)
        self.assertLess(source.index("verifySvix(rawBody"), source.index("JSON.parse(rawBody)"))

    def test_unsubscribe_is_token_scoped_and_does_not_delete_account(self) -> None:
        source = self.read("supabase/functions/email-unsubscribe/index.ts")
        for marker in (
            "apply_stockradar_unsubscribe_v1",
            "List-Unsubscribe",
            "Việc này không xóa tài khoản StockRadar",
            "Ngừng toàn bộ email nội dung",
            "Referrer-Policy",
            "no-store",
        ):
            self.assertIn(marker, source)
        self.assertNotIn("delete-account", source)
        self.assertNotIn("auth.admin.deleteUser", source)

    def test_worker_has_separate_website_and_functions_bases(self) -> None:
        source = self.read("supabase/functions/email-worker/index.ts")
        self.assertIn("STOCKRADAR_PUBLIC_BASE_URL", source)
        self.assertIn("STOCKRADAR_FUNCTIONS_BASE_URL", source)
        self.assertIn('/functions/v1', source)
        self.assertIn("co-phieu/?ticker=", source)


if __name__ == "__main__":
    unittest.main()
