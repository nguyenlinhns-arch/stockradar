import json
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from engine.stockradar.models import Horizon, Recommendation, RecommendationStatus, TrackRecordMode
from engine.stockradar.scoring import HORIZON_BUCKET_WEIGHTS, calculate_horizon_score


ROOT = Path(__file__).resolve().parents[2]


class RecommendationContractTests(unittest.TestCase):
    def test_four_horizon_models_are_distinct_and_total_100(self) -> None:
        profiles = [tuple(weights.items()) for weights in HORIZON_BUCKET_WEIGHTS.values()]
        self.assertEqual(len(profiles), 4)
        self.assertEqual(len(set(profiles)), 4)
        for weights in HORIZON_BUCKET_WEIGHTS.values():
            self.assertEqual(sum(weights.values()), 100)

    def test_horizon_score_keeps_probability_boundary(self) -> None:
        weights = HORIZON_BUCKET_WEIGHTS[Horizon.MEDIUM_TERM]
        result = calculate_horizon_score(Horizon.MEDIUM_TERM, weights)
        self.assertEqual(result.score, 100)
        self.assertEqual(result.coverage_pct, 100)
        self.assertFalse(result.to_dict()["score_is_probability"])

    def test_demo_recommendations_follow_immutable_contract(self) -> None:
        fixture = json.loads((ROOT / "engine" / "fixtures" / "demo_snapshot.json").read_text(encoding="utf-8"))
        records = [Recommendation.from_dict(item) for item in fixture["recommendations"]]
        self.assertEqual(len(records), 5)
        self.assertEqual({record.horizon for record in records}, set(Horizon))
        self.assertTrue(all(record.is_mock for record in records))
        self.assertTrue(all(record.thesis and record.risks and record.invalidation_conditions for record in records))
        self.assertIsNone(next(record for record in records if record.horizon is Horizon.ACCUMULATION).stop_loss)
        self.assertTrue(all(record.record_mode is TrackRecordMode.SHADOW for record in records))

        unactivated = next(record for record in records if record.recommendation_state is RecommendationStatus.UNACTIVATED)
        self.assertFalse(unactivated.is_activated)
        self.assertIsNone(unactivated.performance_entry_price)
        self.assertIsNone(unactivated.current_return_pct)

        closed = [record for record in records if record.is_closed]
        self.assertEqual(len(closed), 2)
        self.assertTrue(all(record.final_return_pct is not None and record.current_return_pct is None for record in closed))
        self.assertTrue(any(record.final_return_pct > 0 for record in closed))
        self.assertTrue(any(record.final_return_pct < 0 for record in closed))
        with self.assertRaises(FrozenInstanceError):
            records[0].current_price = 99  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
