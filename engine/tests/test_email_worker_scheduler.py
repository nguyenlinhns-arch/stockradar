from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCHEDULER_MIGRATION = "supabase/migrations/20260904104000_add_email_worker_scheduler.sql"
GATE_BIND_MIGRATION = "supabase/migrations/20260904104200_bind_email_scheduler_to_delivery_gate.sql"


class EmailWorkerSchedulerTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_scheduler_uses_cron_pgnet_and_vault_without_source_secret(self) -> None:
        migration = self.read(SCHEDULER_MIGRATION)
        for marker in (
            "pg_cron",
            "pg_net",
            "vault.decrypted_secrets",
            "stockradar_email_worker_scheduler_token",
            "net.http_post",
            "private.dispatch_stockradar_email_worker_v1",
            "cron.schedule",
        ):
            self.assertIn(marker, migration)
        self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY", migration)
        self.assertNotIn("RESEND_API_KEY", migration)

    def test_delivery_gate_controls_scheduler_enable_and_disable(self) -> None:
        migration = self.read(GATE_BIND_MIGRATION)
        for marker in (
            "private.sync_email_scheduler_with_delivery_gate_v1",
            "new.sending_enabled is true",
            "scheduler_enabled=true",
            "new.sending_enabled is false",
            "scheduler_enabled=false",
            "email_delivery_gate_sync_scheduler_v1",
            "vault.decrypted_secrets",
        ):
            self.assertIn(marker, migration)

    def test_cron_does_not_make_http_call_without_gate_and_due_email(self) -> None:
        migration = self.read(SCHEDULER_MIGRATION)
        source = migration.lower()
        scheduler_gate_pos = source.index("if v_sched.scheduler_enabled is not true")
        delivery_gate_pos = source.index("if v_sending is not true")
        due_pos = source.index("if v_due is not true")
        http_pos = source.index("net.http_post")
        self.assertLess(scheduler_gate_pos, http_pos)
        self.assertLess(delivery_gate_pos, http_pos)
        self.assertLess(due_pos, http_pos)
        self.assertIn("o.status in ('pending','failed')", source)
        self.assertIn("o.expires_at > now()", source)
        self.assertIn("o.scheduled_at <= now()", source)

    def test_worker_accepts_only_legacy_service_role_or_verified_scheduler_token(self) -> None:
        source = self.read("supabase/functions/email-worker/index.ts")
        lower = source.lower()
        for marker in (
            "supabase_secret_keys",
            "supabase_service_role_key",
            "x-stockradar-scheduler",
            "/^[a-f0-9]{64}$/",
            "verify_stockradar_email_scheduler_token_v1",
            "sha256hex(schedulertoken)",
            'reason:"unauthorized"',
        ):
            self.assertIn(marker, lower)
        self.assertNotIn("stockradar_email_worker_scheduler_token", lower)

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
