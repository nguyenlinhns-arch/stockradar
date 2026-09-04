import csv
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from engine.stockradar.internal_features import RawBar
from engine.stockradar.raw_pipeline import (
    BENCHMARK_METHOD,
    RawPipelineError,
    apply_corporate_actions,
    build_internal_equal_weight_benchmark,
    compute_top_from_bundle,
    write_pipeline_outputs,
)


SNAPSHOT_ID = "hose-raw-2026-09-04-141500-vn"
AS_OF = "2026-09-04T14:15:00+07:00"
NOW = datetime(2026, 9, 4, 7, 20, tzinfo=timezone.utc)


def write_csv(path: Path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class RawPipelineTests(unittest.TestCase):
    def setup_bundle(self, root: Path, *, rights=True):
        tickers = ("AAA", "BBB")
        write_csv(
            root / "security_master.csv",
            ["ticker", "name", "exchange", "sector"],
            [
                {"ticker": "AAA", "name": "Alpha", "exchange": "HOSE", "sector": "Công nghệ"},
                {"ticker": "BBB", "name": "Beta", "exchange": "HOSE", "sector": "Ngân hàng"},
            ],
        )

        start = date(2025, 1, 1)
        ohlcv = []
        for offset in range(252):
            timestamp = (start + timedelta(days=offset)).isoformat()
            for index, ticker in enumerate(tickers):
                base = 20 + offset * (0.10 + index * 0.01)
                if offset == 251:
                    previous = 20 + (offset - 1) * (0.10 + index * 0.01)
                    base = previous * 1.03
                ohlcv.append({
                    "ticker": ticker,
                    "timestamp": timestamp,
                    "open": round(base * 0.995, 6),
                    "high": round(base * 1.01, 6),
                    "low": round(base * 0.99, 6),
                    "close": round(base, 6),
                    "volume": 1_600_000 if offset == 251 else 700_000 + index * 50_000,
                })
        write_csv(root / "ohlcv.csv", ["ticker", "timestamp", "open", "high", "low", "close", "volume"], ohlcv)

        financial_rows = []
        for index, ticker in enumerate(tickers):
            scale = 1 + index * 0.1
            samples = [
                ("2024-12-31", "ANNUAL", 1000, 100, 1200, 600, 150, 80, 120, 35, 50, 150, 30),
                ("2025-12-31", "ANNUAL", 1250, 150, 1450, 720, 160, 100, 190, 45, 50, 210, 35),
                ("2025-06-30", "QUARTER", 220, 20, 1300, 650, 155, 85, 30, 10, 50, 35, 7),
                ("2025-09-30", "QUARTER", 240, 22, 1320, 660, 155, 85, 32, 10, 50, 38, 7),
                ("2025-12-31Q", "QUARTER", 260, 24, 1350, 680, 158, 90, 34, 11, 50, 40, 8),
                ("2026-03-31", "QUARTER", 285, 28, 1400, 700, 160, 95, 38, 12, 50, 45, 8),
                ("2026-06-30", "QUARTER", 340, 35, 1480, 740, 162, 105, 45, 13, 50, 52, 9),
            ]
            for period_end, period_type, revenue, income, assets, equity, debt, cash, cfo, capex, shares, op, da in samples:
                financial_rows.append({
                    "ticker": ticker,
                    "period_end": period_end,
                    "period_type": period_type,
                    "revenue": revenue * scale,
                    "net_income": income * scale,
                    "total_assets": assets * scale,
                    "equity": equity * scale,
                    "total_debt": debt * scale,
                    "cash": cash * scale,
                    "operating_cash_flow": cfo * scale,
                    "capex": capex * scale,
                    "shares_outstanding": shares * scale,
                    "operating_profit": op * scale,
                    "depreciation_amortization": da * scale,
                })
        write_csv(
            root / "fundamentals.csv",
            [
                "ticker", "period_end", "period_type", "revenue", "net_income", "total_assets", "equity",
                "total_debt", "cash", "operating_cash_flow", "capex", "shares_outstanding",
                "operating_profit", "depreciation_amortization",
            ],
            financial_rows,
        )
        write_csv(root / "corporate_actions.csv", ["ticker", "effective_date", "event_type"], [])
        write_csv(root / "events.csv", ["ticker", "event_date", "event_type", "description"], [])

        descriptor = {
            "contract_version": "1.0",
            "snapshot": {
                "snapshot_id": SNAPSHOT_ID,
                "as_of": AS_OF,
                "source_timestamp": AS_OF,
                "exchange": "HOSE",
                "expected_total": 2,
                "scanned_count": 2,
                "valid_count": 2,
                "excluded_count": 0,
                "stale_count": 0,
                "missing_count": 0,
                "data_grade": "DECISION_GRADE",
                "same_snapshot": True,
                "adjusted_basis_consistent": True,
                "corporate_action_checked": True,
                "source": "LICENSED_PROVIDER_RAW_INPUT",
                "exclusion_log": [],
            },
            "rights": {
                "publication_allowed": rights,
                "redistribution_allowed": rights,
                "source_terms_reviewed": rights,
                "evidence_ref": "RAW-RIGHTS-001" if rights else "",
            },
            "active_status": {"semantics_resolved": True, "market_status_checked": True},
            "datasets": {
                "security_master": {"path": "security_master.csv", "ticker_column": "ticker", "exchange_column": "exchange"},
                "ohlcv": {"path": "ohlcv.csv", "ticker_column": "ticker"},
                "fundamentals": {"path": "fundamentals.csv", "ticker_column": "ticker"},
                "corporate_actions": {"path": "corporate_actions.csv"},
                "events": {"path": "events.csv"},
            },
        }
        write_json(root / "descriptor.json", descriptor)
        write_json(root / "research.json", {
            "schema_version": "1.0",
            "calculation_origin": "STOCKRADAR_RESEARCH",
            "items": [
                {"ticker": ticker, "meaning_score": 4.5, "moat_score": 4.0, "management_score": 4.5, "catalyst_score": 4.0, "event_risk_pass": True}
                for ticker in tickers
            ],
        })
        write_json(root / "valuation.json", {
            "schema_version": "1.0",
            "calculation_origin": "STOCKRADAR_RESEARCH",
            "items": [
                {
                    "ticker": ticker,
                    "maintenance_capex": 35,
                    "bear_growth_rate": 0.05,
                    "base_growth_rate": 0.12,
                    "bull_growth_rate": 0.18,
                    "discount_rate": 0.13,
                    "terminal_growth_rate": 0.04,
                    "horizon_years": 5,
                }
                for ticker in tickers
            ],
        })

    def test_raw_bundle_computes_top_hose_with_stockradar_engine_only(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_bundle(root)
            result = compute_top_from_bundle(
                bundle_dir=root,
                descriptor_path=root / "descriptor.json",
                research_path=root / "research.json",
                valuation_path=root / "valuation.json",
                now=NOW,
            )
            public = result.public_payload()
            self.assertTrue(public["ranking_valid"])
            self.assertEqual(public["calculation_origin"], "STOCKRADAR_ENGINE")
            self.assertFalse(public["external_scores_accepted"])
            self.assertEqual(public["benchmark_method"], BENCHMARK_METHOD)
            self.assertEqual(public["scanned_valid_tickers"], 2)
            self.assertEqual(len(result.computations), 2)
            self.assertEqual({row.ticker for row in result.computations}, {"AAA", "BBB"})
            self.assertTrue(all(row.candidate.score_coverage_pct == 100 for row in result.computations))

    def test_public_output_and_private_computation_are_separate(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_bundle(root)
            result = compute_top_from_bundle(
                bundle_dir=root,
                descriptor_path=root / "descriptor.json",
                research_path=root / "research.json",
                valuation_path=root / "valuation.json",
                now=NOW,
            )
            public = root / "out" / "top-stocks.json"
            private = root / "private" / "computations.json"
            write_pipeline_outputs(result, public_top_path=public, private_computations_path=private)
            public_payload = json.loads(public.read_text(encoding="utf-8"))
            private_payload = json.loads(private.read_text(encoding="utf-8"))
            self.assertIn("strongest", public_payload)
            self.assertNotIn("items", public_payload)
            self.assertEqual(len(private_payload["items"]), 2)
            self.assertIn("technical", private_payload["items"][0])
            self.assertIn("fundamental", private_payload["items"][0])
            self.assertIn("valuation", private_payload["items"][0])

    def test_rights_gate_blocks_top_computation_before_ranking(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_bundle(root, rights=False)
            with self.assertRaisesRegex(RawPipelineError, "production raw-data gate failed"):
                compute_top_from_bundle(
                    bundle_dir=root,
                    descriptor_path=root / "descriptor.json",
                    research_path=root / "research.json",
                    valuation_path=root / "valuation.json",
                    now=NOW,
                )

    def test_missing_internal_research_blocks_entire_top_hose(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_bundle(root)
            research = json.loads((root / "research.json").read_text(encoding="utf-8"))
            research["items"] = research["items"][:1]
            write_json(root / "research.json", research)
            with self.assertRaisesRegex(RawPipelineError, "StockRadar research missing"):
                compute_top_from_bundle(
                    bundle_dir=root,
                    descriptor_path=root / "descriptor.json",
                    research_path=root / "research.json",
                    valuation_path=root / "valuation.json",
                    now=NOW,
                )

    def test_internal_equal_weight_benchmark_is_calculated_from_raw_stock_bars(self):
        bars = {
            "AAA": [
                RawBar(timestamp=f"{index:03d}", open=10 + index, high=11 + index, low=9 + index, close=10 + index, volume=1000)
                for index in range(252)
            ],
            "BBB": [
                RawBar(timestamp=f"{index:03d}", open=20 + 2 * index, high=21 + 2 * index, low=19 + 2 * index, close=20 + 2 * index, volume=2000)
                for index in range(252)
            ],
        }
        benchmark = build_internal_equal_weight_benchmark(bars, ["AAA", "BBB"])
        self.assertEqual(len(benchmark), 252)
        self.assertEqual(benchmark[0].close, 100)
        self.assertEqual(benchmark[0].volume, 3000)
        self.assertGreater(benchmark[-1].close, benchmark[0].close)

    def test_corporate_action_share_change_is_adjusted_by_stockradar(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "corporate_actions.csv"
            write_csv(
                path,
                ["ticker", "effective_date", "event_type", "old_shares", "new_shares"],
                [{"ticker": "AAA", "effective_date": "2026-01-03", "event_type": "SHARE_CHANGE", "old_shares": 1, "new_shares": 2}],
            )
            bars = {
                "AAA": [
                    RawBar("2026-01-01", 100, 102, 98, 100, 1000),
                    RawBar("2026-01-02", 110, 112, 108, 110, 1000),
                    RawBar("2026-01-03", 55, 56, 54, 55, 2000),
                ]
            }
            adjusted = apply_corporate_actions(bars, path)["AAA"]
            self.assertEqual(adjusted[0].close, 50)
            self.assertEqual(adjusted[1].close, 55)
            self.assertEqual(adjusted[0].volume, 2000)
            self.assertEqual(adjusted[2].close, 55)

    def test_vendor_like_internal_input_origin_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_bundle(root)
            research = json.loads((root / "research.json").read_text(encoding="utf-8"))
            research["calculation_origin"] = "VENDOR_RATING"
            write_json(root / "research.json", research)
            with self.assertRaisesRegex(RawPipelineError, "calculation_origin must be STOCKRADAR_RESEARCH"):
                compute_top_from_bundle(
                    bundle_dir=root,
                    descriptor_path=root / "descriptor.json",
                    research_path=root / "research.json",
                    valuation_path=root / "valuation.json",
                    now=NOW,
                )


if __name__ == "__main__":
    unittest.main()
