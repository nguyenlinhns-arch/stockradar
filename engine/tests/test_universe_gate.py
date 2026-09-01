import unittest

from engine.stockradar.models import Candidate, DataGrade, MarketRegime, SetupState, UniverseSnapshot
from engine.stockradar.ranking import build_radar, full_universe_gate


def snapshot(**overrides):
    values = {
        "snapshot_id": "S1",
        "as_of": "2026-09-01T15:00:00+07:00",
        "source_timestamp": "2026-09-01T15:00:00+07:00",
        "exchange": "HOSE",
        "expected_total": 5,
        "scanned_count": 5,
        "valid_count": 5,
        "excluded_count": 0,
        "stale_count": 0,
        "missing_count": 0,
        "data_grade": DataGrade.DECISION_GRADE,
        "same_snapshot": True,
        "adjusted_basis_consistent": True,
        "corporate_action_checked": True,
        "source": "TEST",
    }
    values.update(overrides)
    return UniverseSnapshot(**values)


def candidates():
    return [
        Candidate(
            ticker=f"T{index}", score=90 - index, score_coverage_pct=100,
            setup="VCP", state=SetupState.READY, previous_state=SetupState.NEAR_TRIGGER,
            market_regime=MarketRegime.GREEN, current_price=10 + index, pivot=11 + index,
            distance_to_pivot_pct=1, extension_pct=0, liquidity_pass=True,
            event_risk_pass=True, reason="test"
        )
        for index in range(5)
    ]


class UniverseGateTests(unittest.TestCase):
    def test_full_decision_grade_can_publish_top5(self) -> None:
        radar = build_radar(snapshot(), candidates())
        self.assertEqual(radar["status"], "TOP5_HOSE")
        self.assertTrue(radar["is_top5_hose"])

    def test_371_of_374_is_incomplete(self) -> None:
        gate = full_universe_gate(snapshot(expected_total=374, scanned_count=371, valid_count=371))
        self.assertFalse(gate.passed)
        self.assertIn("processed_universe_incomplete", gate.failures)

    def test_mock_data_never_becomes_top5_hose(self) -> None:
        radar = build_radar(snapshot(data_grade=DataGrade.MOCK), candidates())
        self.assertEqual(radar["status"], "SHORTLIST_FROM_AVAILABLE_DATA")
        self.assertFalse(radar["is_top5_hose"])

    def test_stale_record_blocks_full_universe(self) -> None:
        gate = full_universe_gate(snapshot(stale_count=1))
        self.assertIn("stale_records_present", gate.failures)

    def test_missing_exclusion_log_blocks_full_universe(self) -> None:
        gate = full_universe_gate(snapshot(valid_count=4, excluded_count=1))
        self.assertIn("exclusion_log_incomplete", gate.failures)

    def test_high_score_extended_candidate_is_not_ranked(self) -> None:
        pool = candidates()
        pool[0] = Candidate(
            ticker="EXT", score=99, score_coverage_pct=100, setup="BREAKOUT",
            state=SetupState.EXTENDED, previous_state=SetupState.TRIGGERED,
            market_regime=MarketRegime.GREEN, current_price=120, pivot=100,
            distance_to_pivot_pct=-20, extension_pct=20, liquidity_pass=True,
            event_risk_pass=True, reason="extended"
        )
        radar = build_radar(snapshot(), pool)
        self.assertFalse(any(item["ticker"] == "EXT" for item in radar["items"]))
        self.assertFalse(radar["is_top5_hose"])


if __name__ == "__main__":
    unittest.main()

