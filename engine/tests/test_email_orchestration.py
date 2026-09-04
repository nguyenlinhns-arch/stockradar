from pathlib import Path
import unittest

from engine.stockradar.email_orchestration import (
    EmailRecipientContext,
    build_action_email_candidate,
    build_daily_email_candidate,
    build_digest_email_candidate,
)


ROOT = Path(__file__).resolve().parents[2]


class EmailOrchestrationTests(unittest.TestCase):
    def action(self):
        return {
            "ticker": "HPG",
            "horizon": "SHORT_TERM",
            "previous_state": "WAIT",
            "current_state": "BUY",
            "evaluated_at": "2026-09-04T10:30:00+07:00",
            "generated_at": "2026-09-04T10:31:00+07:00",
            "next_review": "11:15",
            "reference_price": 29.1,
            "buy_zone": "28.8-29.3",
            "stop": 27.9,
            "target": 32.0,
            "risk_reward": 2.1,
            "invalidation": "Đóng dưới 27.9",
            "new_position_decision": "MUA",
            "holding_decision": "GIỮ / có thể TĂNG",
            "reasons": ["Giá vào vùng hành động", "Điều kiện xác nhận đã đạt"],
        }

    def test_action_candidate_is_recipient_specific_but_engine_decision_is_source_of_truth(self):
        recipient = EmailRecipientContext(
            user_id="user-1", ticker="HPG", horizon="SHORT_TERM", owns_stock=True, alert_enabled=True
        )
        candidate = build_action_email_candidate(
            recipient,
            self.action(),
            snapshot_id="snapshot-1030",
            decision_ref="recommendation:HPG:short:1030",
            scheduled_at="2026-09-04T10:31:00+07:00",
            expires_at="2026-09-04T11:15:00+07:00",
        )
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.email_kind, "EVENT_ALERT")
        self.assertEqual(candidate.priority, 20)
        self.assertEqual(candidate.payload["headline"], "HPG · CHỜ → MUA")
        self.assertTrue(candidate.payload["decision_card"]["holding_decision"].startswith("GIỮ"))
        self.assertEqual(candidate.decision_ref, "recommendation:HPG:short:1030")
        self.assertTrue(candidate.idempotency_key.startswith("sr:"))
        self.assertEqual(len(candidate.idempotency_key), 67)
        self.assertEqual(candidate.as_rpc_params()["p_email_kind"], "EVENT_ALERT")

    def test_disabled_ticker_alert_does_not_create_candidate(self):
        recipient = EmailRecipientContext(user_id="user-1", ticker="HPG", alert_enabled=False)
        self.assertIsNone(build_action_email_candidate(
            recipient,
            self.action(),
            snapshot_id="snapshot-1030",
            decision_ref="decision-1",
            scheduled_at="2026-09-04T10:31:00+07:00",
            expires_at="2026-09-04T11:15:00+07:00",
        ))

    def test_orchestrator_does_not_allow_same_state_or_context_mismatch(self):
        same = self.action()
        same["current_state"] = "WAIT"
        recipient = EmailRecipientContext(user_id="user-1", ticker="HPG", horizon="SHORT_TERM", alert_enabled=True)
        with self.assertRaisesRegex(ValueError, "NO_MATERIAL_STATE_CHANGE"):
            build_action_email_candidate(
                recipient, same, snapshot_id="s", decision_ref="d",
                scheduled_at="2026-09-04T10:31:00+07:00", expires_at="2026-09-04T11:15:00+07:00"
            )
        with self.assertRaisesRegex(ValueError, "ticker context"):
            build_action_email_candidate(
                EmailRecipientContext(user_id="user-1", ticker="FPT", alert_enabled=True), self.action(),
                snapshot_id="s", decision_ref="d", scheduled_at="2026-09-04T10:31:00+07:00",
                expires_at="2026-09-04T11:15:00+07:00"
            )

    def test_idempotency_is_stable_for_same_decision_and_user(self):
        recipient = EmailRecipientContext(user_id="user-1", ticker="HPG", alert_enabled=True)
        kwargs = dict(
            snapshot_id="snapshot-1030", decision_ref="decision-1",
            scheduled_at="2026-09-04T10:31:00+07:00", expires_at="2026-09-04T11:15:00+07:00"
        )
        first = build_action_email_candidate(recipient, self.action(), **kwargs)
        second = build_action_email_candidate(recipient, self.action(), **kwargs)
        assert first and second
        self.assertEqual(first.idempotency_key, second.idempotency_key)

    def test_daily_and_optional_digests_require_explicit_validity_windows(self):
        daily = build_daily_email_candidate(
            "user-1",
            {
                "report_date": "2026-09-04T09:00:00+07:00",
                "generated_at": "2026-09-04T08:58:00+07:00",
                "market_context": "Trung tính",
                "watchlist_changes": [],
                "stable_watchlist_count": 5,
            },
            snapshot_id="daily-snapshot", report_ref="daily:2026-09-04",
            scheduled_at="2026-09-04T09:00:00+07:00", expires_at="2026-09-04T11:00:00+07:00",
        )
        self.assertEqual(daily.email_kind, "DAILY_BRIEF")
        self.assertIn("Watchlist ổn định", daily.payload["subject"])

        weekly = build_digest_email_candidate(
            "user-1", "WEEKLY_REPORT", {"summary": "Tuần này không có thay đổi cần hành động."},
            snapshot_id=None, digest_ref="week:2026-W36",
            scheduled_at="2026-09-04T17:00:00+07:00", expires_at="2026-09-05T17:00:00+07:00",
        )
        self.assertEqual(weekly.email_kind, "WEEKLY_REPORT")
        with self.assertRaisesRegex(ValueError, "expires_at"):
            build_digest_email_candidate(
                "user-1", "WEEKLY_REPORT", {"summary": "x"}, snapshot_id=None, digest_ref="x",
                scheduled_at="2026-09-04T17:00:00+07:00", expires_at="2026-09-04T16:00:00+07:00"
            )

    def test_orchestration_has_no_provider_or_service_role_secret(self):
        source = (ROOT / "engine" / "stockradar" / "email_orchestration.py").read_text(encoding="utf-8")
        self.assertNotIn("RESEND_API_KEY", source)
        self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY", source)
        self.assertNotIn("requests.post", source)
        self.assertIn("build_premium_action_alert", source)


if __name__ == "__main__":
    unittest.main()
