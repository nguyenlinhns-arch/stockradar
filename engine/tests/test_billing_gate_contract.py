import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase" / "migrations" / "20260903044335_add_billing_foundation_gate.sql"


class BillingGateContractTests(unittest.TestCase):
    def test_checkout_is_fail_closed_and_private(self):
        source = MIGRATION.read_text(encoding="utf-8")
        for marker in (
            "provider_configured boolean not null default false",
            "webhook_signature_verified boolean not null default false",
            "reconciliation_ready boolean not null default false",
            "refund_chargeback_ready boolean not null default false",
            "tax_compliance_approved boolean not null default false",
            "checkout_enabled boolean not null default false",
            "billing_gate_safe_enable",
            "create table private.payment_events",
            "create table private.subscription_grants",
            "unique (provider_name, provider_event_id)",
            "payment_event_id uuid not null unique",
            "raw_payload_sha256",
            "with (security_invoker = true)",
            "revoke all on table private.payment_events from public, anon, authenticated",
        ):
            self.assertIn(marker, source)

    def test_paid_grants_are_thirty_day_verified_events_only(self):
        source = MIGRATION.read_text(encoding="utf-8")
        self.assertIn("duration_days integer not null default 30 check (duration_days = 30)", source)
        self.assertIn("granted_days integer not null default 30 check (granted_days = 30)", source)
        self.assertIn("payment.status = 'PAID'", source)
        self.assertIn("payment.verified_at is not null", source)
        self.assertIn("grant_row.revoked_at is null", source)


if __name__ == "__main__":
    unittest.main()
