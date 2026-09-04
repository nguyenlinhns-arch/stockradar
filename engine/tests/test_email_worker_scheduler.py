from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class EmailWorkerSchedulerTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_scheduler_uses_cron_pgnet_and_vault_without_source_secret(self) -> None:
        migration = self.read("supabase/migrations/20260903103000_schedule_email_worker.sql")
        for marker in (
            "pg_cron",
            "pg_net",
            "vault.decrypted_secrets",
            "stockradar_email_worker_url",
            "stockradar_email_worker_scheduler_token",
            "net.http_post",
            "perform public.run_stockradar_email_worker_v1()",
            "cron.schedule",
        ):
            self.assertIn(marker, migration)
        self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY", migration)
        self.assertNotIn("RESEND_API_KEY", migration)

    def test_delivery_gate_controls_scheduler_enable_and_disable(self) -> None:
        migration = self.read("supabase/migrations/20260903103000_schedule_email_worker.sql")
        for marker in (
            "create or replace function public.set_stockradar_email_delivery_enabled",
            "alter table private.email_delivery_gate disable trigger",
            "alter table private.email_delivery_gate enable trigger",
            "enabled = true",
            "enabled = false",
            "service_role",
            "run_stockradar_email_worker_v1",
        ):
            self.assertIn(marker, migration)

    def test_cron_does_not_make_http_call_without_gate_and_due_email(self) -> None:
        migration = self.read("supabase/migrations/20260903103000_schedule_email_worker.sql")
        source = migration.lower()
        gate_pos = source.index("if not coalesce(v_gate_enabled, false)")
        due_pos = source.index("if not exists (")
        http_pos = source.index("net.http_post")
        self.assertLess(gate_pos, http_pos)
        self.assertLess(due_pos, http_pos)
        self.assertIn("status = 'pending'", source)
        self.assertIn("expires_at > now()", source)

    def test_worker_accepts_only_legacy_service_role_or_verified_scheduler_token(self) -> None:
        source = self.read("supabase/functions/email-worker/index.ts")
        for marker in (
            "SUPABASE_SECRET_KEYS",
            "SUPABASE_SERVICE_ROLE_KEY",
            "X-StockRadar-Scheduler",
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
            self.assertIn(f"[functions.{function_name}]\nverify_jwt = false", config)


if __name__ == "__main__":
    unittest.main()
