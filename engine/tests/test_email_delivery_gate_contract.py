import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "supabase" / "migrations"


class EmailDeliveryGateContractTests(unittest.TestCase):
    def test_email_foundation_is_private_and_fail_closed(self):
        source = (MIGRATIONS / "20260903043820_add_product_email_consent_outbox.sql").read_text(encoding="utf-8")
        for marker in (
            "create schema if not exists private",
            "create table private.email_outbox",
            "create table private.email_suppressions",
            "create table public.product_email_preferences",
            "create table public.product_email_consent_events",
            "to authenticated",
            "auth.uid()",
            "product email requires active TRIAL or PAID account",
            "revoke all on table private.email_outbox from public, anon, authenticated",
        ):
            self.assertIn(marker, source)

    def test_privileged_profile_trigger_is_moved_to_private_schema(self):
        source = (MIGRATIONS / "20260903043838_move_email_entitlement_trigger_private.sql").read_text(encoding="utf-8")
        self.assertIn("private.disable_stockradar_product_email_on_ineligible_profile", source)
        self.assertIn("security definer", source.lower())
        self.assertIn("set search_path = ''", source)
        self.assertIn("revoke all on function", source)

    def test_delivery_gate_cannot_be_enabled_partially(self):
        source = (MIGRATIONS / "20260903043921_add_email_delivery_gate.sql").read_text(encoding="utf-8")
        for marker in (
            "provider_configured boolean not null default false",
            "sender_domain_verified boolean not null default false",
            "unsubscribe_ready boolean not null default false",
            "bounce_complaint_ready boolean not null default false",
            "compliance_approved boolean not null default false",
            "sending_enabled boolean not null default false",
            "email_delivery_gate_safe_enable",
            "and gate.sending_enabled",
            "consent.document_version = gate.current_consent_version",
            "suppression.user_id is null",
            "eligible_to_send",
        ):
            self.assertIn(marker, source)
        self.assertIn("with (security_invoker = true)", source)
        self.assertIn("revoke all on private.product_email_eligibility", source)


if __name__ == "__main__":
    unittest.main()
