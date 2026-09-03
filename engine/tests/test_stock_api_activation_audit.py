import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase" / "migrations" / "20260903050533_add_stock_api_activation_audit.sql"
REVOCATION_MIGRATION = ROOT / "supabase" / "migrations" / "20260903050718_auto_disable_stock_api_on_approval_revoke.sql"


class StockApiActivationAuditTests(unittest.TestCase):
    def test_approvals_and_activation_events_are_private_append_only_tables(self):
        source = MIGRATION.read_text(encoding="utf-8")
        for marker in (
            "create table private.stock_api_approval_events",
            "create table private.stock_api_activation_events",
            "approval_type in ('DATA_RIGHTS','COMPLIANCE')",
            "manifest_ref ~ '^sha256:[0-9a-f]{64}$'",
            "alter table private.stock_api_approval_events enable row level security",
            "alter table private.stock_api_activation_events enable row level security",
            "revoke all on table private.stock_api_approval_events from public, anon, authenticated",
            "revoke all on table private.stock_api_activation_events from public, anon, authenticated",
        ):
            self.assertIn(marker, source)

    def test_activation_requires_current_rights_and_compliance_approvals(self):
        source = MIGRATION.read_text(encoding="utf-8")
        for marker in (
            "event.approval_type = 'DATA_RIGHTS'",
            "event.approval_type = 'COMPLIANCE'",
            "order by event.recorded_at desc, event.id desc",
            "current DATA_RIGHTS approval is required",
            "current COMPLIANCE approval is required",
        ):
            self.assertIn(marker, source)

    def test_activation_requires_fresh_cache_for_exact_manifest_and_snapshot(self):
        source = MIGRATION.read_text(encoding="utf-8")
        for marker in (
            "report.source_manifest_ref = v_manifest",
            "report.snapshot_id = v_snapshot",
            "report.expires_at > now()",
            "at least one fresh manifest-bound report is required",
            "active_manifest_ref = v_manifest",
            "active_snapshot_id = v_snapshot",
            "api_enabled = true",
        ):
            self.assertIn(marker, source)

    def test_activation_functions_are_service_role_only(self):
        source = MIGRATION.read_text(encoding="utf-8")
        for function_signature in (
            "public.record_stockradar_api_approval(text, text, text, boolean, text)",
            "public.activate_stockradar_api(text, text, text)",
            "public.deactivate_stockradar_api(text)",
        ):
            self.assertIn(f"revoke all on function {function_signature} from public, anon, authenticated", source)
            self.assertIn(f"grant execute on function {function_signature} to service_role", source)
        self.assertGreaterEqual(source.lower().count("security definer"), 3)
        self.assertGreaterEqual(source.count("set search_path = ''"), 3)

    def test_deactivation_closes_gate_and_records_event(self):
        source = MIGRATION.read_text(encoding="utf-8")
        for marker in (
            "api_enabled = false",
            "data_ready = false",
            "data_rights_approved = false",
            "compliance_approved = false",
            "active_manifest_ref = null",
            "active_snapshot_id = null",
            "'DISABLE'",
        ):
            self.assertIn(marker, source)

    def test_approval_revocation_auto_closes_matching_active_gate(self):
        source = REVOCATION_MIGRATION.read_text(encoding="utf-8")
        for marker in (
            "if p_granted is false then",
            "v_active_manifest = v_manifest and v_active_snapshot = v_snapshot",
            "api_enabled = false",
            "data_ready = false",
            "data_rights_approved = false",
            "compliance_approved = false",
            "active_manifest_ref = null",
            "active_snapshot_id = null",
            "'AUTO_REVOKE:' || v_type || ':' || v_evidence",
            "'DISABLE'",
        ):
            self.assertIn(marker, source)

    def test_approval_revocation_serializes_with_activation_and_remains_service_role_only(self):
        source = REVOCATION_MIGRATION.read_text(encoding="utf-8")
        self.assertIn("pg_advisory_xact_lock(hashtextextended('stockradar-api-activation', 0))", source)
        self.assertIn("security definer", source.lower())
        self.assertIn("set search_path = ''", source)
        signature = "public.record_stockradar_api_approval(text, text, text, boolean, text)"
        self.assertIn(f"revoke all on function {signature} from public, anon, authenticated", source)
        self.assertIn(f"grant execute on function {signature} to service_role", source)


if __name__ == "__main__":
    unittest.main()
