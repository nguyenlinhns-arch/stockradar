import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase" / "migrations" / "20260904042030_add_stock_api_request_observability.sql"
EDGE = ROOT / "supabase" / "functions" / "stock-api" / "index.ts"


class StockApiObservabilityTests(unittest.TestCase):
    def test_request_audit_is_private_and_service_role_only(self):
        source = MIGRATION.read_text(encoding="utf-8")
        for marker in (
            "create table private.stock_api_request_events",
            "alter table private.stock_api_request_events enable row level security",
            "revoke all on table private.stock_api_request_events from public, anon, authenticated, service_role",
            "create or replace function public.record_stockradar_api_request_event",
            "security definer",
            "set search_path = ''",
            "revoke all on function public.record_stockradar_api_request_event",
            "grant execute on function public.record_stockradar_api_request_event",
            "to service_role",
        ):
            self.assertIn(marker, source)

    def test_request_audit_collects_only_operational_metadata(self):
        source = MIGRATION.read_text(encoding="utf-8")
        for marker in (
            "user_id uuid",
            "account_tier text",
            "ticker text",
            "horizon text",
            "outcome text",
            "reason text",
            "http_status smallint",
            "latency_ms integer",
            "rate_limit_remaining integer",
        ):
            self.assertIn(marker, source)

        lowered = source.lower()
        for forbidden in (
            "jwt",
            "authorization",
            "user_agent",
            "user-agent",
            "ip_address",
            "email text",
            "payload json",
        ):
            self.assertNotIn(forbidden, lowered)

    def test_edge_function_audits_authenticated_outcomes_without_logging_secrets(self):
        source = EDGE.read_text(encoding="utf-8")
        for marker in (
            'client.rpc("record_stockradar_api_request_event"',
            "p_http_status: status",
            "p_latency_ms: latencyMs",
            "p_rate_limit_remaining",
            '"INVALID_TICKER"',
            '"PREMIUM_REQUIRED"',
            '"RATE_LIMITED"',
            '"REPORT_RPC_FAILED"',
            '"READY"',
            '"NOT_FOUND"',
            "performance.now()",
        ):
            self.assertIn(marker, source)

        self.assertNotIn("console.log(token", source)
        self.assertNotIn("console.log(authorization", source)
        self.assertNotIn("p_token", source)
        self.assertNotIn("p_email", source)
        self.assertNotIn("p_ip", source)


if __name__ == "__main__":
    unittest.main()
