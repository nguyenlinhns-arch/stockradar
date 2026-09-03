import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase" / "migrations" / "20260903045301_bind_stock_api_cache_to_manifest.sql"


class StockApiCacheBindingTests(unittest.TestCase):
    def test_api_safe_enable_requires_manifest_and_snapshot(self):
        source = MIGRATION.read_text(encoding="utf-8")
        for marker in (
            "active_manifest_ref text",
            "active_snapshot_id text",
            "length(trim(coalesce(active_manifest_ref, ''))) > 0",
            "length(trim(coalesce(active_snapshot_id, ''))) > 0",
        ):
            self.assertIn(marker, source)

    def test_cache_writer_is_service_role_only_and_validates_payload(self):
        source = MIGRATION.read_text(encoding="utf-8")
        for marker in (
            "public.upsert_stockradar_cached_report",
            "payload must be a JSON object",
            "source_manifest_ref is required",
            "invalid cache time window",
            "on conflict (ticker, horizon) do update",
            "revoke all on function public.upsert_stockradar_cached_report",
            "to service_role",
        ):
            self.assertIn(marker, source)
        self.assertIn("security definer", source.lower())
        self.assertIn("set search_path = ''", source)

    def test_fetch_blocks_manifest_or_snapshot_mismatch(self):
        source = MIGRATION.read_text(encoding="utf-8")
        for marker in (
            "v_report.source_manifest_ref <> v_gate.active_manifest_ref",
            "v_report.snapshot_id <> v_gate.active_snapshot_id",
            "CACHE_MANIFEST_MISMATCH",
            "REPORT_STALE",
            "BLOCKED_DATA_GATE",
        ):
            self.assertIn(marker, source)


if __name__ == "__main__":
    unittest.main()
