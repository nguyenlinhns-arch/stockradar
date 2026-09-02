import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from engine.stockradar.models import Horizon, RecommendationStatus, ReviewDecision
from engine.stockradar.personalization import (
    AccountTier,
    EmailKind,
    UserPreferences,
    can_receive_email,
)
from engine.stockradar.recommendation import (
    assess_new_and_holding_positions,
    empty_recommendation_publication,
    recommendation_state_after_review,
    review_is_due,
)
from engine.stockradar.today_changes import ChangeEvent, today_changes


ROOT = Path(__file__).resolve().parents[2]


class V21ProductRulesTests(unittest.TestCase):
    def test_r2_no_gate_pass_can_publish_no_recommendation_message(self) -> None:
        result = empty_recommendation_publication()
        self.assertFalse(result["published"])
        self.assertEqual(result["items"], [])
        self.assertIn("KHÔNG CÓ KHUYẾN NGHỊ MỚI", result["message"])

    def test_r3_new_buy_and_holding_questions_are_independent(self) -> None:
        result = assess_new_and_holding_positions(
            price_extended=True,
            thesis_intact=True,
            holding_risk_triggered=False,
        )
        self.assertEqual(result.new_position_state, "KHÔNG MUA ĐUỔI")
        self.assertEqual(result.holding_state, "TIẾP TỤC THEO DÕI")

    def test_r4_due_review_is_mandatory_and_has_deterministic_decisions(self) -> None:
        now = datetime(2026, 9, 2, tzinfo=timezone.utc)
        self.assertTrue(review_is_due("2026-09-01T00:00:00+00:00", now=now))
        self.assertTrue(review_is_due(None, now=now))
        self.assertEqual(
            recommendation_state_after_review(RecommendationStatus.ACTIVE, ReviewDecision.CONTINUE),
            RecommendationStatus.ACTIVE,
        )
        self.assertEqual(
            recommendation_state_after_review(RecommendationStatus.ACTIVE, ReviewDecision.CLOSE),
            RecommendationStatus.CLOSED,
        )

    def test_r5_event_schema_is_append_only_and_correction_is_a_new_event(self) -> None:
        schema = (ROOT / "track-record" / "schema.sql").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temp:
            db = sqlite3.connect(Path(temp) / "ledger.sqlite")
            db.executescript(schema)
            db.execute(
                """INSERT INTO snapshots (
                    snapshot_id, as_of, source_timestamp, exchange, source, data_grade,
                    universe_total, scanned_total, valid_total, excluded_total, coverage_pct,
                    market_regime, release_status, raw_payload
                ) VALUES ('S','2026-09-01','2026-09-01','HOSE','TEST','MOCK',1,1,1,0,100,'YELLOW','TEST','{}')"""
            )
            db.execute(
                """INSERT INTO recommendations (
                    recommendation_id,snapshot_id,ticker,horizon,publication_timestamp,
                    generated_at,published_at,system_version,score_version,publish_status,
                    record_mode,data_grade,raw_payload,is_mock
                ) VALUES ('R','S','AAA','SHORT_TERM','2026-09-01','2026-09-01',
                    '2026-09-01','2.1.2','s','TEST','SHADOW','MOCK','{}',1)"""
            )
            db.execute(
                """INSERT INTO recommendation_events (
                    recommendation_id,event_type,event_at,state,new_state,snapshot_id,
                    system_version,created_by,audit_reference,payload_json
                ) VALUES ('R','PUBLISHED','2026-09-01','UNACTIVATED','UNACTIVATED','S',
                    '2.1.2','SYSTEM','AUDIT-R-PUB','{}')"""
            )
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE recommendation_events SET state='ACTIVE'")
            db.execute(
                """INSERT INTO recommendation_events (
                    recommendation_id,event_type,event_at,state,new_state,snapshot_id,
                    system_version,created_by,audit_reference,correction_of,payload_json
                ) VALUES ('R','CORRECTION','2026-09-02','UNACTIVATED','UNACTIVATED','S',
                    '2.1.2','SYSTEM','AUDIT-R-CORR',1,'{}')"""
            )
            self.assertEqual(db.execute("SELECT COUNT(*) FROM recommendation_events").fetchone()[0], 2)
            db.close()

    def test_r6_free_user_never_receives_daily_product_email(self) -> None:
        self.assertFalse(
            can_receive_email(
                AccountTier.FREE,
                EmailKind.PRODUCT_DAILY,
                email_verified=True,
                product_consent=True,
            )
        )
        self.assertTrue(
            can_receive_email(
                AccountTier.FREE,
                EmailKind.TRANSACTIONAL,
                email_verified=False,
            )
        )

    def test_r7_trial_and_paid_email_are_verified_consent_based_and_personalized(self) -> None:
        self.assertTrue(
            can_receive_email(
                AccountTier.TRIAL,
                EmailKind.PRODUCT_DAILY,
                email_verified=True,
                product_consent=True,
            )
        )
        self.assertFalse(
            can_receive_email(
                AccountTier.PAID,
                EmailKind.PRODUCT_DAILY,
                email_verified=False,
                product_consent=True,
            )
        )
        preferences = UserPreferences.create([Horizon.MEDIUM_TERM], ["Thép"], ["HPG"])
        ordered = preferences.prioritize([
            {"ticker": "FPT", "horizon": "SHORT_TERM", "sector": "Công nghệ"},
            {"ticker": "HPG", "horizon": "MEDIUM_TERM", "sector": "Thép"},
        ])
        self.assertEqual(ordered[0]["ticker"], "HPG")

    def test_r8_r9_r11_internal_fixture_preserves_closed_and_unactivated_truth(self) -> None:
        payload = json.loads((ROOT / "engine/fixtures/demo_snapshot.json").read_text(encoding="utf-8"))
        closed = [item for item in payload["recommendations"] if item["status"] == "CLOSED"]
        unactivated = [item for item in payload["recommendations"] if item["recommendation_state"] == "UNACTIVATED"]
        self.assertTrue(any(item["final_return_pct"] > 0 for item in closed))
        self.assertTrue(any(item["final_return_pct"] < 0 for item in closed))
        self.assertTrue(all(item["current_return_pct"] is None for item in closed))
        self.assertTrue(all(item.get("final_return_pct") is None for item in unactivated))

    def test_r10_benchmark_records_store_the_same_recommendation_window(self) -> None:
        records = json.loads((ROOT / "engine/fixtures/demo_snapshot.json").read_text(encoding="utf-8"))
        for item in records["recommendations"]:
            if item["benchmark_return_pct"] is None:
                continue
            expected = (item["vnindex_current_or_close"] / item["vnindex_at_activation"] - 1) * 100
            self.assertAlmostEqual(expected, item["benchmark_return_pct"], places=2)

    def test_r12_public_lookup_keeps_four_horizon_shell_fail_closed(self) -> None:
        payload = json.loads((ROOT / "website/public/data/stock-reports.json").read_text(encoding="utf-8"))
        script = (ROOT / "website/assets/app.js").read_text(encoding="utf-8")
        self.assertEqual(payload["data_status"], "BLOCKED_DATA_GATE")
        self.assertEqual(payload["items"], [])
        self.assertIn("Object.entries(horizonLabels)", script)
        for horizon in Horizon:
            self.assertIn(horizon.value, script)

    def test_today_changes_filters_low_value_noise(self) -> None:
        events = [
            ChangeEvent("1", "HPG", "STATE_CHANGED", "2026-09-01T10:00:00Z", "HPG", "Changed", 3),
            ChangeEvent("2", "HPG", "OBSERVED", "2026-09-01T11:00:00Z", "HPG", "Price tick", 1),
        ]
        self.assertEqual([item.event_id for item in today_changes(events)], ["1"])


if __name__ == "__main__":
    unittest.main()
