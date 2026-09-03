import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase" / "migrations" / "20260903044849_add_authenticated_stock_api_gateway.sql"
EDGE = ROOT / "supabase" / "functions" / "stock-api" / "index.ts"


class StockApiGatewayContractTests(unittest.TestCase):
    def test_database_gateway_is_fail_closed_and_private(self):
        source = MIGRATION.read_text(encoding="utf-8")
        for marker in (
            "data_ready boolean not null default false",
            "data_rights_approved boolean not null default false",
            "compliance_approved boolean not null default false",
            "api_enabled boolean not null default false",
            "stock_api_gate_safe_enable",
            "create table private.stock_report_cache",
            "create table private.stock_api_rate_limit_policies",
            "create table private.stock_api_rate_limit_windows",
            "security definer",
            "set search_path = ''",
            "grant execute on function public.consume_stockradar_api_quota(uuid, text) to service_role",
            "grant execute on function public.fetch_stockradar_cached_report(text, text) to service_role",
            "revoke all on function public.consume_stockradar_api_quota(uuid, text) from public, anon, authenticated",
            "revoke all on function public.fetch_stockradar_cached_report(text, text) from public, anon, authenticated",
        ):
            self.assertIn(marker, source)

    def test_rate_limit_is_per_authenticated_profile_tier(self):
        source = MIGRATION.read_text(encoding="utf-8")
        for marker in (
            "from public.profiles p",
            "v_status <> 'ACTIVE'",
            "pg_advisory_xact_lock",
            "'FREE', 'stock_report', 30, 60",
            "'TRIAL', 'stock_report', 90, 60",
            "'PAID', 'stock_report', 180, 60",
            "'RATE_LIMITED'",
            "'retry_after'",
        ):
            self.assertIn(marker, source)

    def test_report_fetch_blocks_disabled_or_stale_data(self):
        source = MIGRATION.read_text(encoding="utf-8")
        for marker in (
            "'BLOCKED_DATA_GATE'",
            "'PRODUCTION_API_DISABLED'",
            "'REPORT_STALE'",
            "v_report.expires_at <= now()",
            "source_manifest_ref text not null",
        ):
            self.assertIn(marker, source)

    def test_edge_function_requires_user_jwt_and_premium_tier_before_service_role_report(self):
        source = EDGE.read_text(encoding="utf-8")
        for marker in (
            "authClient.auth.getUser(token)",
            'Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")',
            'const PREMIUM_TIERS = new Set(["TRIAL", "PAID"])',
            '.select("account_tier,account_status")',
            'PREMIUM_TIERS.has(accountTier)',
            '"PREMIUM_REQUIRED"',
            'serviceClient.rpc("consume_stockradar_api_quota"',
            'serviceClient.rpc("fetch_stockradar_cached_report"',
            'p_bucket: "stock_report"',
            '"RATE_LIMITED"',
            '"Retry-After"',
            '"Cache-Control": "no-store"',
            '"https://stockradar.vn"',
        ):
            self.assertIn(marker, source)
        self.assertLess(source.index('PREMIUM_TIERS.has(accountTier)'), source.index('serviceClient.rpc("consume_stockradar_api_quota"'))
        self.assertNotIn("console.log(authorization", source)
        self.assertNotIn("console.log(token", source)
        self.assertNotIn("verify_jwt", source.lower())


if __name__ == "__main__":
    unittest.main()