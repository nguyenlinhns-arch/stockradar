import unittest

from engine.stockradar.scoring import DoubleCountError, calculate_score


class ScoringTests(unittest.TestCase):
    def test_full_score_has_exact_value(self) -> None:
        result = calculate_score(
            {
                "trend": 18,
                "vpa": 13,
                "sepa_canslim": 17,
                "relative_strength": 8,
                "fundamental": 12,
                "valuation": 7,
                "catalyst": 4,
                "risk_liquidity": 5,
            }
        )
        self.assertEqual(result.score, 84)
        self.assertEqual(result.coverage_pct, 100)
        self.assertEqual(result.range_low, result.range_high)

    def test_missing_bucket_returns_range_not_normalized_score(self) -> None:
        result = calculate_score({"trend": 18, "vpa": 12})
        self.assertIsNone(result.score)
        self.assertEqual(result.coverage_pct, 35)
        self.assertEqual(result.range_low, 30)
        self.assertEqual(result.range_high, 95)

    def test_double_count_is_rejected(self) -> None:
        with self.assertRaises(DoubleCountError):
            calculate_score(
                {"trend": 15, "vpa": 12},
                {"trend": ["breakout-1"], "vpa": ["breakout-1"]},
            )

    def test_score_is_explicitly_not_probability(self) -> None:
        result = calculate_score({name: 0 for name in (
            "trend", "vpa", "sepa_canslim", "relative_strength",
            "fundamental", "valuation", "catalyst", "risk_liquidity"
        )})
        self.assertFalse(result.to_dict()["score_is_probability"])


if __name__ == "__main__":
    unittest.main()

