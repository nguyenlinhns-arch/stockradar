import unittest

from engine.stockradar.probability import CalibrationEvidence, publishable_probability
from engine.stockradar.volume import validate_intraday_volume_method


class RegressionRuleTests(unittest.TestCase):
    def test_naive_intraday_vs_full_day_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_intraday_volume_method("partial_vs_full_day_adv")

    def test_same_time_rvol_is_allowed(self) -> None:
        validate_intraday_volume_method("same_time_rvol")

    def test_projection_requires_method(self) -> None:
        with self.assertRaises(ValueError):
            validate_intraday_volume_method("projected_full_session")

    def test_uncalibrated_score_has_no_numeric_probability(self) -> None:
        self.assertIsNone(publishable_probability(None))

    def test_matching_oos_calibration_can_publish(self) -> None:
        evidence = CalibrationEvidence(
            probability_pct=62, sample_size=500, method="isotonic OOS",
            oos=True, same_setup=True, same_regime=True, same_horizon=True,
            same_universe=True, costs_included=True
        )
        self.assertEqual(publishable_probability(evidence), 62)

    def test_mismatched_horizon_calibration_is_blocked(self) -> None:
        evidence = CalibrationEvidence(
            probability_pct=62, sample_size=500, method="isotonic OOS",
            oos=True, same_setup=True, same_regime=True, same_horizon=False,
            same_universe=True, costs_included=True
        )
        self.assertIsNone(publishable_probability(evidence))


if __name__ == "__main__":
    unittest.main()

