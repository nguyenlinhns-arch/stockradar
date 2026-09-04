from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class EmailDeliveryActivationAuditTests(unittest.TestCase):
    def test_activation_requires_all_current_approvals_and_is_service_role_only(self) -> None:
        sql = (ROOT / "supabase" / "migrations" / "20260904102500_add_email_delivery_activation_audit.sql").read_text(encoding="utf-8")
        for marker in (
            "email_delivery_approval_events",
            "email_delivery_activation_events",
            "PROVIDER_CONFIG",
            "SENDER_DOMAIN",
            "UNSUBSCRIBE",
            "BOUNCE_COMPLAINT",
            "COMPLIANCE",
            "activate_stockradar_email_delivery_v1",
            "current PROVIDER_CONFIG approval required",
            "current SENDER_DOMAIN approval required",
            "current UNSUBSCRIBE approval required",
            "current BOUNCE_COMPLAINT approval required",
            "current COMPLIANCE approval required",
            "sending_enabled=true",
            "to service_role",
        ):
            self.assertIn(marker, sql)
        self.assertIn("revoke insert, update, delete on private.email_delivery_gate from service_role", sql)
        self.assertNotIn("grant execute on function public.activate_stockradar_email_delivery_v1(text,text) to authenticated", sql)

    def test_approval_revoke_auto_disables_live_delivery(self) -> None:
        sql = (ROOT / "supabase" / "migrations" / "20260904102500_add_email_delivery_activation_audit.sql").read_text(encoding="utf-8")
        for marker in (
            "auto_disable_email_delivery_on_approval_revoke_v1",
            "AUTO_DISABLE",
            "sending_enabled=false",
            "APPROVAL_REVOKED:",
            "email_delivery_approval_revoke_auto_disable_v1",
        ):
            self.assertIn(marker, sql)

    def test_deactivation_is_audited_and_does_not_need_to_destroy_valid_evidence(self) -> None:
        sql = (ROOT / "supabase" / "migrations" / "20260904102500_add_email_delivery_activation_audit.sql").read_text(encoding="utf-8")
        self.assertIn("deactivate_stockradar_email_delivery_v1", sql)
        self.assertIn("values('DISABLE'", sql)
        self.assertIn("update private.email_delivery_gate set sending_enabled=false", sql)


if __name__ == "__main__":
    unittest.main()
