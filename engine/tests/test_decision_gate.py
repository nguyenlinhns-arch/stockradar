import unittest

from engine.stockradar.decision import BuyGateInput, evaluate_buy_gate, signal_is_current
from engine.stockradar.models import DataGrade, MarketRegime


def valid_input(**overrides):
    values = dict(
        data_grade=DataGrade.DECISION_GRADE,
        market_regime=MarketRegime.GREEN,
        setup_pass=True,
        score_coverage_pass=True,
        trigger_pass=True,
        volume_pass=True,
        extension_pass=True,
        liquidity_pass=True,
        event_risk_pass=True,
        corporate_action_pass=True,
        rr=3.0,
        stop_exists=True,
        horizon_consistent=True,
        execution_pass=True,
        portfolio_pass=True,
    )
    values.update(overrides)
    return BuyGateInput(**values)


class DecisionGateTests(unittest.TestCase):
    def test_all_gates_pass(self) -> None:
        result = evaluate_buy_gate(valid_input())
        self.assertTrue(result.passed)
        self.assertEqual(result.action, "MUA")

    def test_market_red_blocks_buy(self) -> None:
        result = evaluate_buy_gate(valid_input(market_regime=MarketRegime.RED))
        self.assertEqual(result.action, "THEO DÕI")
        self.assertIn("market_regime", result.failures)

    def test_research_grade_blocks_current_action(self) -> None:
        result = evaluate_buy_gate(valid_input(data_grade=DataGrade.RESEARCH_GRADE))
        self.assertEqual(result.action, "RESEARCH ONLY")

    def test_low_rr_blocks_buy(self) -> None:
        result = evaluate_buy_gate(valid_input(rr=1.5))
        self.assertEqual(result.action, "CHỜ MUA")
        self.assertIn("risk_reward", result.failures)

    def test_missing_stop_blocks_buy(self) -> None:
        self.assertFalse(evaluate_buy_gate(valid_input(stop_exists=False)).passed)

    def test_mismatched_horizon_blocks_buy(self) -> None:
        self.assertIn("horizon", evaluate_buy_gate(valid_input(horizon_consistent=False)).failures)

    def test_old_signal_invalid_after_market_change(self) -> None:
        self.assertFalse(signal_is_current("S1", "S2", True, True, False))


if __name__ == "__main__":
    unittest.main()

