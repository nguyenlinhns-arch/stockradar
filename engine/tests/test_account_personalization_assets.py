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
            'name="cost_basis"',
            'name="portfolio_weight_pct"',
            "data-position-context-fields",
            "Dữ liệu tự khai báo",
        ):
            self.assertIn(marker, source)
        for forbidden in ("NAV", "OTP hay quyền giao dịch"):
            self.assertNotIn(f'name="{forbidden}"', source)
        self.assertNotIn('name="quantity"', source)
        self.assertNotIn('name="broker_account"', source)

    def test_personalization_client_uses_supabase_owned_rows(self):
        source = (WEBSITE / "assets" / "account-preferences.js").read_text(encoding="utf-8")
        for marker in (
            ".from('profiles')",
            ".from('user_preferences')",
            ".from('watchlist_items')",
            ".eq('user_id', user.id)",
            "alert_enabled: false",
            "cost_basis",
            "portfolio_weight_pct",
            "syncPositionFields",
            "Giá vốn phải lớn hơn 0",
            "Tỷ trọng phải nằm trong khoảng 0–100%",
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

    def test_optional_position_context_migration_is_constrained_and_ownership_bound(self):
        migration = (
            ROOT / "supabase" / "migrations" / "20260904142000_add_optional_position_context.sql"
        ).read_text(encoding="utf-8")
        for marker in (
            "cost_basis numeric(18,4)",
            "portfolio_weight_pct numeric(5,2)",
            "watchlist_cost_basis_positive",
            "watchlist_portfolio_weight_range",
            "watchlist_position_context_requires_ownership",
            "owns_stock = true",
            "cost_basis is null and portfolio_weight_pct is null",
            "not brokerage data",
        ):
            self.assertIn(marker, migration)
        self.assertNotIn("quantity", migration.lower())
        self.assertNotIn("broker_account", migration.lower())


if __name__ == "__main__":
    unittest.main()
