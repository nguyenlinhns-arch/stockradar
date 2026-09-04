import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EDGE = ROOT / "supabase" / "functions" / "delete-account" / "index.ts"
CLIENT = ROOT / "website" / "assets" / "auth-delete-security.js"
RECENT_SESSION = ROOT / "supabase" / "migrations" / "20260904042834_require_recent_session_for_account_deletion.sql"
BILLING_HISTORY = ROOT / "supabase" / "migrations" / "20260904042655_allow_account_deletion_with_billing_history.sql"


class AccountDeletionContractTests(unittest.TestCase):
    def test_browser_requires_password_reauthentication_before_delete_call(self):
        source = CLIENT.read_text(encoding="utf-8")
        for marker in (
            "delete_current_password",
            "signInWithPassword",
            "DELETE_ACCOUNT",
            "client.functions.invoke('delete-account'",
            "XOA",
        ):
            self.assertIn(marker, source)
        self.assertLess(source.index("signInWithPassword"), source.index("client.functions.invoke('delete-account'"))

    def test_delete_edge_requires_verified_user_and_recent_session(self):
        source = EDGE.read_text(encoding="utf-8")
        for marker in (
            'auth.getUser(token)',
            "verifiedJwtPayload(token)",
            "session_id",
            'admin.rpc(',
            '"verify_stockradar_recent_session"',
            "p_max_age_seconds: 300",
            '"RECENT_REAUTH_REQUIRED"',
            'admin.auth.admin.deleteUser(user.id)',
            '"Cache-Control": "no-store"',
            "rawBody.length > 4096",
        ):
            self.assertIn(marker, source)
        self.assertLess(source.index("auth.getUser(token)"), source.index("verifiedJwtPayload(token)"))
        self.assertLess(source.index("verify_stockradar_recent_session"), source.index("admin.auth.admin.deleteUser(user.id)"))
        self.assertNotIn("console.log(token", source)
        self.assertNotIn("console.log(authHeader", source)

    def test_recent_session_rpc_is_service_role_only(self):
        source = RECENT_SESSION.read_text(encoding="utf-8")
        for marker in (
            "from auth.sessions s",
            "s.id = p_session_id",
            "s.user_id = p_user_id",
            "s.created_at >= now() - make_interval",
            "revoke all on function public.verify_stockradar_recent_session",
            "from public, anon, authenticated",
            "to service_role",
        ):
            self.assertIn(marker, source)

    def test_billing_audit_survives_account_deletion_without_blocking_it(self):
        source = BILLING_HISTORY.read_text(encoding="utf-8")
        self.assertGreaterEqual(source.count("alter column user_id drop not null"), 2)
        self.assertGreaterEqual(source.count("on delete set null"), 2)
        self.assertIn("payment_events_user_id_fkey", source)
        self.assertIn("subscription_grants_user_id_fkey", source)
        self.assertNotIn("on delete cascade", source.lower())


if __name__ == "__main__":
    unittest.main()
