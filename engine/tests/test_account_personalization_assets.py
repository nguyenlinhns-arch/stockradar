import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WEBSITE = ROOT / "website"


class AccountPersonalizationAssetTests(unittest.TestCase):
    def test_account_page_exposes_persistent_personalization_controls(self):
        source = (WEBSITE / "tai-khoan" / "index.html").read_text(encoding="utf-8")
        for marker in (
            "data-account-personalization",
            "data-account-preferences-form",
            "data-account-watchlist-form",
            "data-account-watchlist",
            "data-watchlist-limit",
            "account-preferences.js",
        ):
            self.assertIn(marker, source)
        for forbidden in ("NAV", "giá vốn", "OTP hay quyền giao dịch"):
            # These phrases may only appear in the explicit privacy statement, never as input names.
            self.assertNotIn(f'name="{forbidden}"', source)

    def test_personalization_client_uses_supabase_owned_rows(self):
        source = (WEBSITE / "assets" / "account-preferences.js").read_text(encoding="utf-8")
        for marker in (
            ".from('profiles')",
            ".from('user_preferences')",
            ".from('watchlist_items')",
            ".eq('user_id', user.id)",
            "alert_enabled: false",
        ):
            self.assertIn(marker, source)
        for forbidden in ("service_role", "sb_secret_", "access_token", "refresh_token", "trading_token"):
            self.assertNotIn(forbidden, source.lower())

    def test_supabase_migration_has_rls_grants_and_server_side_limits(self):
        migration = (
            ROOT / "supabase" / "migrations" / "20260903043404_add_personalization_watchlist.sql"
        ).read_text(encoding="utf-8")
        for marker in (
            "alter table public.user_preferences enable row level security",
            "alter table public.watchlist_items enable row level security",
            "to authenticated",
            "auth.uid()",
            "watchlist limit reached for tier",
            "when tier = 'PAID' then 20 else 3",
            "revoke all on table public.user_preferences from anon, authenticated",
            "revoke all on table public.watchlist_items from anon, authenticated",
        ):
            self.assertIn(marker, migration)
        self.assertNotIn("security definer", migration.lower())
        self.assertNotIn("user_metadata", migration.lower())


if __name__ == "__main__":
    unittest.main()
