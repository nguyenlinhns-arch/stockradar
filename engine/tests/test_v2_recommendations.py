import unittest

from engine.stockradar.models import DataGrade, Horizon, RecommendationStatus
from engine.stockradar.performance import (
    CorporateAction,
    CorporateActionType,
    PerformanceError,
    PriceBar,
    activate_on_first_eligible_bar,
    calculate_excess_return,
    calculate_return,
)
from engine.stockradar.recommendation import RecommendationGateInput, evaluate_recommendation_gate


class RecommendationGateV2Tests(unittest.TestCase):
    def base_input(self, **overrides):
        values = {
            "horizon": Horizon.SHORT_TERM,
            "data_grade": DataGrade.DECISION_GRADE,
            "stale": False,
            "horizon_score": 85,
            "score_threshold": 80,
            "score_coverage_pct": 100,
            "minimum_coverage_pct": 100,
            "liquidity_pass": True,
            "event_risk_pass": True,
            "extension_pass": True,
            "market_pass": True,
            "evidence_pass": True,
            "horizon_consistent": True,
            "unresolved_contradictions": 0,
            "entry_valid": True,
            "target_valid": True,
            "stop_or_risk_valid": True,
            "risk_reward": 2.5,
        }
        values.update(overrides)
        return RecommendationGateInput(**values)

    def test_ranking_strength_does_not_bypass_recommendation_gate(self) -> None:
        result = evaluate_recommendation_gate(self.base_input(extension_pass=False, horizon_score=99))
        self.assertFalse(result.can_publish)
        self.assertEqual(result.public_state, RecommendationStatus.WAIT_BUY)
        self.assertIn("extension", result.failures)

    def test_full_short_term_gate_publishes_unactivated_record(self) -> None:
        result = evaluate_recommendation_gate(self.base_input())
        self.assertTrue(result.can_publish)
        self.assertEqual(result.public_state, RecommendationStatus.UNACTIVATED)

    def test_long_term_does_not_require_tactical_stop_or_rr(self) -> None:
        result = evaluate_recommendation_gate(
            self.base_input(
                horizon=Horizon.LONG_TERM,
                entry_valid=None,
                target_valid=None,
                stop_or_risk_valid=None,
                risk_reward=None,
            )
        )
        self.assertTrue(result.can_publish)


class PerformanceMethodologyV2Tests(unittest.TestCase):
    def test_activation_uses_first_post_publication_touch_not_daily_low(self) -> None:
        result = activate_on_first_eligible_bar(
            publication_timestamp="2026-08-27T15:00:00+07:00",
            buy_low=50.8,
            buy_high=52.0,
            bars=[
                PriceBar("2026-08-27T14:30:00+07:00", 51.2, 52.3, 50.2, 51.8),
                PriceBar("2026-08-28T10:30:00+07:00", 50.2, 51.4, 49.9, 51.2),
            ],
        )
        self.assertTrue(result.activated)
        self.assertEqual(result.performance_entry_price, 50.8)
        self.assertEqual(result.method, "FIRST_TOUCH_LOWER_BOUND")

    def test_no_trade_in_zone_means_no_activation_and_no_pl(self) -> None:
        result = activate_on_first_eligible_bar(
            publication_timestamp="2026-08-27T15:00:00+07:00",
            buy_low=39.0,
            buy_high=39.4,
            bars=[PriceBar("2026-08-28T10:30:00+07:00", 38.0, 38.7, 37.8, 38.4)],
        )
        self.assertFalse(result.activated)
        self.assertIsNone(result.performance_entry_price)

    def test_price_and_total_return_handle_resolved_actions(self) -> None:
        result = calculate_return(
            100,
            52,
            [
                CorporateAction("split-2-for-1", CorporateActionType.STOCK_SPLIT, "2026-08-29", price_factor=0.5),
                CorporateAction("cash", CorporateActionType.CASH_DIVIDEND, "2026-08-30", cash_per_share=2),
            ],
        )
        self.assertEqual(result.price_return_pct, 4.0)
        self.assertEqual(result.total_return_pct, 8.0)
        self.assertEqual(calculate_excess_return(result.total_return_pct, 3.0), 5.0)

    def test_unresolved_rights_issue_blocks_performance(self) -> None:
        with self.assertRaises(PerformanceError):
            calculate_return(
                20,
                21,
                [CorporateAction("rights", CorporateActionType.RIGHTS_ISSUE, "2026-08-30")],
            )


if __name__ == "__main__":
    unittest.main()
