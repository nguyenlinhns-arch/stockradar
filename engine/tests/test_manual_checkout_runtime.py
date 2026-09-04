from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase" / "migrations" / "20260904111932_add_manual_vietqr_checkout_runtime.sql"


class ManualCheckoutRuntimeTests(unittest.TestCase):
    def source(self) -> str:
        return MIGRATION.read_text(encoding="utf-8")

    def test_checkout_requests_are_private_user_bound_and_time_limited(self):
        source = self.source().lower()
        for marker in (
            "create table if not exists private.checkout_requests",
            "user_id uuid not null references auth.users(id)",
            "payment_reference text not null unique",
            "interval '30 minutes'",
            "alter table private.checkout_requests enable row level security",
            "revoke all on table private.checkout_requests from public, anon, authenticated",
            "auth.uid()",
            "where id = p_checkout_id and user_id = uid",
        ):
            self.assertIn(marker, source)

    def test_browser_can_create_confirm_and_read_but_never_self_grant_paid(self):
        source = self.source().lower()
        self.assertIn("create or replace function public.create_my_checkout_request", source)
        self.assertIn("create or replace function public.confirm_my_checkout_request", source)
        self.assertIn("create or replace function public.get_my_checkout_request", source)
        self.assertIn("grant execute on function public.create_my_checkout_request(text) to authenticated", source)
        self.assertIn("grant execute on function public.confirm_my_checkout_request(uuid) to authenticated", source)
        self.assertIn("grant execute on function public.get_my_checkout_request(uuid) to authenticated", source)
        confirm_start = source.index("create or replace function public.confirm_my_checkout_request")
        verify_start = source.index("create or replace function private.verify_manual_checkout")
        confirm_body = source[confirm_start:verify_start]
        self.assertNotIn("insert into private.payment_events", confirm_body)
        self.assertNotIn("insert into private.subscription_grants", confirm_body)
        self.assertNotIn("account_tier = 'paid'", confirm_body)

    def test_only_private_verified_payment_can_grant_exact_thirty_days(self):
        source = self.source().lower()
        for marker in (
            "create or replace function private.verify_manual_checkout",
            "revoke all on function private.verify_manual_checkout(uuid, text) from public, anon, authenticated",
            "grant execute on function private.verify_manual_checkout(uuid, text) to service_role",
            "status = 'paid'",
            "verified_at",
            "insert into private.subscription_grants",
            "make_interval(days => plan_row.duration_days)",
            "values ('advanced_test', 199000, 30, true)",
            "account_tier = 'paid'",
        ):
            self.assertIn(marker, source)

    def test_checkout_is_fail_closed_until_real_bank_configuration_is_enabled(self):
        source = self.source().lower()
        self.assertIn("create table if not exists private.manual_checkout_config", source)
        self.assertIn("enabled boolean not null default false", source)
        self.assertIn("manual_checkout_config_safe_enable", source)
        self.assertIn("gate_row.checkout_enabled is not true", source)
        self.assertIn("upper(coalesce(gate_row.provider_name, '')) <> 'manual_vietqr'", source)
        self.assertIn("config_row.enabled is not true", source)
        self.assertIn("raise exception 'checkout_disabled'", source)

    def test_paid_expiry_downgrades_to_free_without_deleting_account(self):
        source = self.source().lower()
        self.assertIn("create or replace function private.sync_stockradar_paid_entitlements", source)
        self.assertIn("set account_tier = 'free'", source)
        self.assertIn("not exists", source)
        self.assertIn("stockradar-sync-paid-entitlements", source)
        self.assertIn("17 * * * *", source)
        self.assertNotIn("delete from public.profiles", source)


if __name__ == "__main__":
    unittest.main()
