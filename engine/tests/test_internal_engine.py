import unittest

from engine.stockradar.internal_engine import (
    InternalStockComputation,
    build_top_hose_from_internal,
    compute_stock,
)
from engine.stockradar.internal_features import (
    InternalValuationAssumptions,
    RawBar,
    RawFinancialPeriod,
    StockRadarResearchAssessment,
    compute_fundamental_features,
    compute_technical_features,
    same_time_rvol,
)
from engine.stockradar.models import DataGrade, UniverseSnapshot


class InternalEngineTests(unittest.TestCase):
    def bars(self, *, benchmark=False):
        rows = []
        for index in range(252):
            base = (100.0 + index * 0.03) if benchmark else (20.0 + index * 0.10)
            if index == 251 and not benchmark:
                base = rows[-1].close * 1.03
            volume = 1_600_000 if index == 251 and not benchmark else (700_000 if not benchmark else 5_000_000)
            rows.append(RawBar(
                timestamp=f"{index:04d}",
                open=base * 0.995,
                high=base * 1.01,
                low=base * 0.99,
                close=base,
                volume=volume,
            ))
        return rows

    def financials(self):
        return [
            RawFinancialPeriod("2024", "ANNUAL", 1000, 100, 1200, 600, 150, 80, 120, 35, 50, 150, 30),
            RawFinancialPeriod("2025", "ANNUAL", 1250, 150, 1450, 720, 160, 100, 190, 45, 50, 210, 35),
            RawFinancialPeriod("2025Q2", "QUARTER", 220, 20, 1300, 650, 155, 85, 30, 10, 50),
            RawFinancialPeriod("2025Q3", "QUARTER", 240, 22, 1320, 660, 155, 85, 32, 10, 50),
            RawFinancialPeriod("2025Q4", "QUARTER", 260, 24, 1350, 680, 158, 90, 34, 11, 50),
            RawFinancialPeriod("2026Q1", "QUARTER", 285, 28, 1400, 700, 160, 95, 38, 12, 50),
            RawFinancialPeriod("2026Q2", "QUARTER", 340, 35, 1480, 740, 162, 105, 45, 13, 50),
        ]

    def research(self):
        return StockRadarResearchAssessment(
            meaning_score=4.5,
            moat_score=4.0,
            management_score=4.5,
            catalyst_score=4.0,
            event_risk_pass=True,
        )

    def valuation(self):
        return InternalValuationAssumptions(
            maintenance_capex=35,
            bear_growth_rate=0.05,
            base_growth_rate=0.12,
            bull_growth_rate=0.18,
            discount_rate=0.13,
            terminal_growth_rate=0.04,
            horizon_years=5,
        )

    def snapshot(self):
        return UniverseSnapshot(
            snapshot_id="raw-snapshot-1",
            as_of="2026-09-04T14:15:00+07:00",
            source_timestamp="2026-09-04T14:15:00+07:00",
            exchange="HOSE",
            expected_total=1,
            scanned_count=1,
            valid_count=1,
            excluded_count=0,
            stale_count=0,
            missing_count=0,
            data_grade=DataGrade.DECISION_GRADE,
            same_snapshot=True,
            adjusted_basis_consistent=True,
            corporate_action_checked=True,
            source="LICENSED_PROVIDER_RAW_INPUT",
        )

    def test_technical_features_are_computed_from_raw_ohlcv(self):
        features = compute_technical_features(self.bars(), benchmark_bars=self.bars(benchmark=True))
        self.assertTrue(features.trend_template_pass)
        self.assertEqual(features.stage, "STAGE_2")
        self.assertGreater(features.ma50, features.ma150)
        self.assertGreater(features.avg_volume20, 500_000)
        self.assertGreater(features.volume_ratio20, 2.0)
        self.assertTrue(features.confirmed_breakout)
        self.assertIsNotNone(features.relative_strength_50_pct)
        self.assertIsNotNone(features.relative_strength_200_pct)

    def test_fundamental_ratios_are_derived_from_raw_line_items(self):
        features = compute_fundamental_features(self.financials(), current_price=45)
        self.assertEqual(features.quarterly_revenue_growth_yoy_pct, 54.5455)
        self.assertEqual(features.quarterly_net_income_growth_yoy_pct, 75.0)
        self.assertGreater(features.roe_pct, 20)
        self.assertGreater(features.free_cash_flow, 0)
        self.assertGreater(features.eps, 0)
        self.assertGreater(features.pe, 0)
        self.assertGreater(features.pb, 0)
        self.assertGreater(features.ev_to_ebitda, 0)

    def test_same_time_rvol_is_stockradar_calculation(self):
        self.assertEqual(same_time_rvol(1_500_000, [900_000, 1_000_000, 1_100_000, 1_000_000, 1_000_000]), 1.5)

    def test_compute_stock_builds_full_internal_score_and_candidate(self):
        result = compute_stock(
            ticker="AAA",
            sector="Công nghệ",
            bars=self.bars(),
            benchmark_bars=self.bars(benchmark=True),
            financial_periods=self.financials(),
            research=self.research(),
            valuation_assumptions=self.valuation(),
        )
        self.assertEqual(result.computation["calculation_origin"], "STOCKRADAR_ENGINE")
        self.assertFalse(result.computation["external_scores_accepted"])
        self.assertEqual(result.candidate.score_coverage_pct, 100)
        self.assertGreaterEqual(result.candidate.score, 0)
        self.assertLessEqual(result.candidate.score, 100)
        self.assertTrue(result.candidate.liquidity_pass)
        self.assertEqual(set(result.bucket_scores), {
            "trend", "vpa", "sepa_canslim", "relative_strength",
            "fundamental", "valuation", "catalyst", "risk_liquidity",
        })
        self.assertIn("calculation_origin=STOCKRADAR_ENGINE", result.candidate.evidence)
        self.assertGreater(result.valuation.base_fair_value, 0)

    def test_top_hose_can_be_built_from_internal_computations(self):
        result = compute_stock(
            ticker="AAA",
            sector="Công nghệ",
            bars=self.bars(),
            benchmark_bars=self.bars(benchmark=True),
            financial_periods=self.financials(),
            research=self.research(),
            valuation_assumptions=self.valuation(),
        )
        payload = build_top_hose_from_internal(self.snapshot(), [result])
        self.assertTrue(payload["ranking_valid"])
        self.assertEqual(payload["strongest"][0]["ticker"], "AAA")
        self.assertEqual(payload["strongest"][0]["calculated_by"], "STOCKRADAR_ENGINE")

    def test_top_hose_rejects_tampered_computation_origin(self):
        result = compute_stock(
            ticker="AAA",
            sector="Công nghệ",
            bars=self.bars(),
            benchmark_bars=self.bars(benchmark=True),
            financial_periods=self.financials(),
            research=self.research(),
            valuation_assumptions=self.valuation(),
        )
        tampered = InternalStockComputation(
            ticker=result.ticker,
            sector=result.sector,
            business_model=result.business_model,
            candidate=result.candidate,
            technical=result.technical,
            fundamental=result.fundamental,
            valuation=result.valuation,
            research=result.research,
            valuation_assumptions=result.valuation_assumptions,
            bucket_scores=result.bucket_scores,
            computation={**result.computation, "calculation_origin": "EXTERNAL_PROVIDER"},
        )
        with self.assertRaisesRegex(ValueError, "StockRadar internal computations only"):
            build_top_hose_from_internal(self.snapshot(), [tampered])


if __name__ == "__main__":
    unittest.main()
