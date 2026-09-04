from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class EmailWorkerSchedulerTests(unittest.TestCase):
    def test_scheduler_uses_cron_pgnet_and_vault_without_source_secret(self) -> None:
        sql = (ROOT / "supabase" / "migrations" / "20260904104000_add_email_worker_scheduler.sql").read_text(encoding="utf-8")
        for marker in (
            "create extension if not exists pg_cron",
            "create extension if not exists pg_net",
            "email_worker_scheduler_gate",
            "vault.create_secret",
            "stockradar_email_worker_scheduler_token",
            "encode(gen_random_bytes(32),'hex')",
            "verify_stockradar_email_scheduler_token_v1",
            "dispatch_stockradar_email_worker_v1",
            "scheduler_enabled is not true",
            "sending_enabled",
            "NO_DUE_EMAIL",
            "net.http_post",
            "x-stockradar-scheduler",
            "*/2 2-11 * * 1-5",
            "stockradar-email-worker-drain-v1",
        ):
            self.assertIn(marker, sql)
        self.assertNotIn("re_", sql)
        self.assertNotIn("service_role_key", sql.lower())
        self.assertNotIn("grant execute on function public.verify_stockradar_email_scheduler_token_v1(text) to authenticated", sql)

    def test_cron_does_not_make_http_call_without_gate_and_due_email(self) -> None:
        sql = (ROOT / "supabase" / "migrations" / "20260904104000_add_email_worker_scheduler.sql").read_text(encoding="utf-8")
        self.assertLess(sql.index("SCHEDULER_DISABLED"), sql.index("net.http_post"))
        self.assertLess(sql.index("DELIVERY_GATE_CLOSED"), sql.index("net.http_post"))
        self.assertLess(sql.index("NO_DUE_EMAIL"), sql.index("net.http_post"))
        self.assertLess(sql.index("SCHEDULER_SECRET_INVALID"), sql.index("net.http_post"))

    def test_delivery_gate_controls_scheduler_enable_and_disable(self) -> None:
        sql = (ROOT / "supabase" / "migrations" / "20260904104200_bind_email_scheduler_to_delivery_gate.sql").read_text(encoding="utf-8")
        for marker in (
            "sync_email_scheduler_with_delivery_gate_v1",
            "scheduler must be configured before delivery activation",
            "Vault token is missing or invalid",
            "scheduler_enabled=true",
            "ENABLED_BY_EMAIL_DELIVERY_GATE",
            "scheduler_enabled=false",
            "DISABLED_BY_EMAIL_DELIVERY_GATE",
            "before update of sending_enabled",
        ):
            self.assertIn(marker, sql)

    def test_worker_accepts_only_legacy_service_role_or_verified_scheduler_token(self) -> None:
        source = (ROOT / "supabase" / "functions" / "email-worker" / "index.ts").read_text(encoding="utf-8")
        for marker in (
            "authorizedServiceRequest",
            'admin.legacy && req.headers.get("authorization") === `Bearer ${admin.key}`',
            'req.headers.get("x-stockradar-scheduler")',
            "/^[a-f0-9]{64}$/",
            "verify_stockradar_email_scheduler_token_v1",
            "sha256Hex(schedulerToken)",
            'reason:"UNAUTHORIZED"',
        ):
            self.assertIn(marker, source)
        self.assertNotIn("stockradar_email_worker_scheduler_token", source)

    def test_email_functions_prefer_new_secret_api_keys_and_persist_no_jwt_gateway(self) -> None:
        for relative in (
            "supabase/functions/email-worker/index.ts",
            "supabase/functions/email-unsubscribe/index.ts",
            "supabase/functions/email-webhook/index.ts",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("SUPABASE_SECRET_KEYS", source)
            self.assertIn("sb_secret_", source)
            self.assertIn("SUPABASE_SERVICE_ROLE_KEY", source)
        config = (ROOT / "supabase" / "config.toml").read_text(encoding="utf-8")
        for function_name in ("email-worker", "email-unsubscribe", "email-webhook"):
            self.assertIn(f"[functions.{function_name}]", config)
        self.assertEqual(config.count("verify_jwt = false"), 3)


if __name__ == "__main__":
    unittest.main()
