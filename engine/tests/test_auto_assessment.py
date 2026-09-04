import unittest

from engine.stockradar.auto_assessment import (
    BusinessModel,
    classify_business_model,
    compute_financial_valuation_features,
    derive_research_assessment,
    derive_valuation_assumptions,
)
from engine.stockradar.internal_engine import compute_stock
from engine.stockradar.internal_features import RawBar, RawFinancialPeriod


class AutoAssessmentTests(unittest.TestCase):
    def bars(self, *, benchmark=False):
        rows = []
        for index in range(252):
            base = (100 + index * 0.025) if benchmark else (18 + index * 0.08)
            if index == 251 and not benchmark:
                base = rows[-1].close * 1.025
            rows.append(RawBar(
                timestamp=f"{index:04d}",
                open=base * 0.995,
                high=base * 1.01,
                low=base * 0.99,
                close=base,
                volume=1_500_000 if index == 251 and not benchmark else (750_000 if not benchmark else 10_000_000),
            ))
        return rows

    def corporate_periods(self):
        return [
            RawFinancialPeriod("2022", "ANNUAL", 800, 70, 1100, 500, 220, 60, 90, 30, 100, 110, 20),
            RawFinancialPeriod("2023", "ANNUAL", 900, 82, 1180, 545, 215, 65, 105, 32, 100, 125, 22),
            RawFinancialPeriod("2024", "ANNUAL", 1030, 100, 1280, 600, 205, 72, 125, 34, 100, 145, 24),
            RawFinancialPeriod("2025", "ANNUAL", 1220, 135, 1420, 690, 200, 85, 175, 36, 100, 190, 26),
            RawFinancialPeriod("2025Q2", "QUARTER", 230, 22, 1320, 630, 205, 75, 31, 9, 100),
            RawFinancialPeriod("2025Q3", "QUARTER", 245, 24, 1340, 640, 205, 77, 32, 9, 100),
            RawFinancialPeriod("2025Q4", "QUARTER", 260, 26, 1360, 655, 202, 79, 34, 10, 100),
            RawFinancialPeriod("2026Q1", "QUARTER", 280, 30, 1400, 675, 200, 82, 38, 10, 100),
            RawFinancialPeriod("2026Q2", "QUARTER", 320, 35, 1450, 710, 198, 88, 44, 11, 100),
        ]

    def bank_periods(self):
        return [
            RawFinancialPeriod("2022", "ANNUAL", 1900, 220, 25000, 1900, 21000, 2800, 0, 0, 100),
            RawFinancialPeriod("2023", "ANNUAL", 2150, 255, 28000, 2050, 23500, 3100, 0, 0, 100),
            RawFinancialPeriod("2024", "ANNUAL", 2450, 300, 31500, 2250, 26400, 3500, 0, 0, 100),
            RawFinancialPeriod("2025", "ANNUAL", 2820, 350, 35000, 2500, 29200, 3900, 0, 0, 100),
            RawFinancialPeriod("2025Q2", "QUARTER", 620, 72, 33000, 2350, 27600, 3650, 0, 0, 100),
            RawFinancialPeriod("2025Q3", "QUARTER", 655, 78, 33500, 2380, 28000, 3700, 0, 0, 100),
            RawFinancialPeriod("2025Q4", "QUARTER", 690, 84, 34000, 2420, 28400, 3750, 0, 0, 100),
            RawFinancialPeriod("2026Q1", "QUARTER", 720, 90, 34500, 2470, 28800, 3820, 0, 0, 100),
            RawFinancialPeriod("2026Q2", "QUARTER", 790, 101, 35500, 2570, 29600, 3980, 0, 0, 100),
        ]

    def test_business_model_is_stockradar_classification(self):
        self.assertEqual(classify_business_model("Ngân hàng"), BusinessModel.BANK)
        self.assertEqual(classify_business_model("Chứng khoán"), BusinessModel.SECURITIES)
        self.assertEqual(classify_business_model("Thép"), BusinessModel.CORPORATE)

    def test_auto_research_and_valuation_are_computed_from_raw_periods(self):
        periods = self.corporate_periods()
        research = derive_research_assessment(periods)
        assumptions = derive_valuation_assumptions(periods)
        self.assertGreater(research.meaning_score, 0)
        self.assertGreater(research.moat_score, 0)
        self.assertGreater(research.management_score, 0)
        self.assertGreaterEqual(research.catalyst_score, 0)
        self.assertGreater(assumptions.maintenance_capex, 0)
        self.assertGreater(assumptions.bull_growth_rate, assumptions.base_growth_rate)
        self.assertGreater(assumptions.base_growth_rate, assumptions.bear_growth_rate)

    def test_bank_uses_equity_roe_valuation_not_corporate_fcf(self):
        periods = self.bank_periods()
        assumptions = derive_valuation_assumptions(periods, business_model=BusinessModel.BANK)
        valuation = compute_financial_valuation_features(periods, current_price=25, assumptions=assumptions)
        self.assertEqual(assumptions.maintenance_capex, 0)
        self.assertGreater(valuation.base_fair_value, 0)
        self.assertGreaterEqual(valuation.bull_fair_value, valuation.base_fair_value)
        self.assertGreaterEqual(valuation.base_fair_value, valuation.bear_fair_value)
        self.assertGreater(valuation.normalized_owner_earnings, 0)

    def test_compute_stock_auto_mode_needs_no_external_research_or_assumptions(self):
        result = compute_stock(
            ticker="AAA",
            sector="Công nghệ",
            company_name="AAA Corp",
            bars=self.bars(),
            benchmark_bars=self.bars(benchmark=True),
            financial_periods=self.corporate_periods(),
        )
        self.assertEqual(result.business_model, "CORPORATE")
        self.assertEqual(result.computation["research_origin"], "STOCKRADAR_ENGINE")
        self.assertEqual(result.computation["valuation_assumption_origin"], "STOCKRADAR_ENGINE")
        self.assertFalse(result.computation["external_research_scores_accepted"])
        self.assertEqual(result.candidate.score_coverage_pct, 100)

    def test_bank_auto_mode_does_not_penalize_bank_for_corporate_debt_logic(self):
        result = compute_stock(
            ticker="BBB",
            sector="Ngân hàng",
            company_name="BBB Bank",
            bars=self.bars(),
            benchmark_bars=self.bars(benchmark=True),
            financial_periods=self.bank_periods(),
        )
        self.assertEqual(result.business_model, "BANK")
        self.assertIsNone(result.fundamental.cfo_to_net_income)
        self.assertIsNone(result.fundamental.ev_to_ebitda)
        self.assertGreater(result.valuation.base_fair_value, 0)
        self.assertEqual(result.candidate.score_coverage_pct, 100)


if __name__ == "__main__":
    unittest.main()
