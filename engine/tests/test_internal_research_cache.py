from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class InternalResearchCacheContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_internal_cache_is_private_and_never_public_action_enabled(self):
        migration = self.read("supabase/migrations/20260904122731_add_internal_stock_research_cache.sql").lower()
        self.assertIn("private.stock_research_cache", migration)
        self.assertIn("public_action_allowed boolean not null default false", migration)
        self.assertIn("check (public_action_allowed is false)", migration)
        self.assertIn("revoke all on table private.stock_research_cache from public, anon, authenticated", migration)
        self.assertIn("grant select, insert, update, delete on table private.stock_research_cache to service_role", migration)

    def test_internal_cache_rpc_is_service_role_only(self):
        migration = self.read("supabase/migrations/20260904122731_add_internal_stock_research_cache.sql").lower()
        self.assertIn("public.upsert_stockradar_internal_research_context", migration)
        self.assertIn("public.fetch_stockradar_internal_research_context", migration)
        self.assertIn("revoke all on function public.upsert_stockradar_internal_research_context", migration)
        self.assertIn("revoke all on function public.fetch_stockradar_internal_research_context", migration)
        self.assertIn("to service_role", migration)
        self.assertIn("internal research payload cannot be public-action enabled", migration)

    def test_sync_is_hose_only_priority_first_and_fail_closed(self):
        script = self.read("scripts/sync_internal_research_cache.py")
        self.assertIn('PRIORITY_TICKERS = ("MBB", "HPG", "ACB")', script)
        self.assertIn('if str(bundle.get("exchange") or "").upper() != "HOSE"', script)
        self.assertIn('release.get("public_action_allowed") is not False', script)
        self.assertIn('release.get("internal_research_ready") is not True', script)
        self.assertIn('expected != len(tickers)', script)
        self.assertIn('"SUPABASE_SECRET_KEYS"', script)
        self.assertIn('"SUPABASE_SERVICE_ROLE_KEY"', script)
        self.assertIn('headers["Authorization"] = f"Bearer {secret_key}"', script)
        self.assertIn('if not is_new_secret_key:', script)
        self.assertNotIn("SUPABASE_SECRET_KEY=", script)
        self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY=", script)


if __name__ == "__main__":
    unittest.main()
