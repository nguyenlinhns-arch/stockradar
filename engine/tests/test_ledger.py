import sqlite3
import tempfile
import unittest
from pathlib import Path

from engine.stockradar.ledger import ImmutableLedger
from engine.stockradar.models import Candidate, DataGrade, MarketRegime, SetupState, UniverseSnapshot
from engine.stockradar.ranking import build_radar


def make_radar():
    snap = UniverseSnapshot(
        snapshot_id="LEDGER-1", as_of="2026-09-01T15:00:00+07:00",
        source_timestamp="2026-09-01T15:00:00+07:00", exchange="HOSE",
        expected_total=1, scanned_count=1, valid_count=1, excluded_count=0,
        stale_count=0, missing_count=0, data_grade=DataGrade.MOCK,
        same_snapshot=True, adjusted_basis_consistent=True,
        corporate_action_checked=True, source="TEST"
    )
    candidate = Candidate(
        ticker="DEMO", score=80, score_coverage_pct=100, setup="VCP",
        state=SetupState.READY, previous_state=SetupState.NEAR_TRIGGER,
        market_regime=MarketRegime.YELLOW, current_price=10, pivot=10.2,
        distance_to_pivot_pct=1.96, extension_pct=0, liquidity_pass=True,
        event_risk_pass=True, reason="fixture", is_mock=True
    )
    return build_radar(snap, [candidate], limit=1)


class LedgerTests(unittest.TestCase):
    def test_snapshot_is_immutable_and_correction_is_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            ledger = ImmutableLedger(Path(temp) / "ledger.sqlite")
            try:
                ledger.initialize()
                ledger.append_radar(make_radar())
                self.assertEqual(ledger.snapshot_count(), 1)
                with self.assertRaises(sqlite3.IntegrityError):
                    ledger.connection.execute(
                        "UPDATE snapshots SET market_regime='GREEN' WHERE snapshot_id='LEDGER-1'"
                    )
                ledger.append_correction(
                    "LEDGER-1", "Test correction", {"market_regime": "GREEN"},
                    "2026-09-01T16:00:00+07:00"
                )
                count = ledger.connection.execute("SELECT COUNT(*) FROM corrections").fetchone()[0]
                self.assertEqual(count, 1)
            finally:
                ledger.close()

    def test_duplicate_snapshot_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            ledger = ImmutableLedger(Path(temp) / "ledger.sqlite")
            try:
                ledger.initialize()
                ledger.append_radar(make_radar())
                with self.assertRaises(sqlite3.IntegrityError):
                    ledger.append_radar(make_radar())
            finally:
                ledger.close()

    def test_recommendation_and_lifecycle_events_are_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            ledger = ImmutableLedger(Path(temp) / "ledger.sqlite")
            try:
                ledger.initialize()
                ledger.append_radar(make_radar())
                record = {
                    "recommendation_id": "REC-LEDGER-1",
                    "snapshot_id": "LEDGER-1",
                    "ticker": "DEMO",
                    "horizon": "SHORT_TERM",
                    "publication_date": "2026-09-01",
                    "publication_time": "15:00:00+07:00",
                    "recommended_buy_low": 10.0,
                    "recommended_buy_high": 10.2,
                    "price_at_publication": 9.9,
                    "generated_at": "2026-09-01T14:55:00+07:00",
                    "published_at": "2026-09-01T15:00:00+07:00",
                    "system_version": "2.0-test",
                    "score_version": "short-v2-test",
                    "publish_status": "DEMO_ONLY",
                    "record_mode": "SHADOW",
                    "data_grade": "MOCK",
                    "is_mock": True,
                }
                ledger.append_recommendation(record)
                ledger.append_recommendation_event(
                    "REC-LEDGER-1", "ACTIVATED", "2026-09-02T10:30:00+07:00",
                    "ACTIVE", {"performance_entry_price": 10.0}
                )
                with self.assertRaises(sqlite3.IntegrityError):
                    ledger.connection.execute(
                        "UPDATE recommendations SET price_at_publication=9.5 WHERE recommendation_id='REC-LEDGER-1'"
                    )
                with self.assertRaises(sqlite3.IntegrityError):
                    ledger.connection.execute(
                        "UPDATE recommendation_events SET performance_entry_price=9.5 WHERE recommendation_id='REC-LEDGER-1'"
                    )
            finally:
                ledger.close()


if __name__ == "__main__":
    unittest.main()
