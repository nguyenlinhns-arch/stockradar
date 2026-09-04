from __future__ import annotations

import csv
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from engine.stockradar.datacore_raw_fundamentals import (
    DATACORE_ANNUAL_DATASET,
    DATACORE_QUARTERLY_DATASET,
    DataCoreCredentials,
    DataCoreRawFundamentalsError,
    OUTPUT_FIELDS,
    acquire_fundamentals,
    normalize_financial_row,
    read_hose_shares,
    reconcile_rows,
    write_fundamentals,
)


class Frame:
    def __init__(self, records):
        self.records = records

    def to_dict(self, orient="records"):
        assert orient == "records"
        return self.records


class FakeClient:
    def __init__(self, annual, quarterly):
        self.annual = annual
        self.quarterly = quarterly
        self.calls = []

    def paginate(self, dataset_code, *, limit=100, max_pages=None):
        self.calls.append((dataset_code, limit, max_pages))
        rows = self.annual if dataset_code == DATACORE_ANNUAL_DATASET else self.quarterly
        yield Frame(rows)


def raw_row(symbol="FPT", year=2025, quarter=None, revenue=1000, net_income=100):
    row = {
        "symbol": symbol,
        "year": year,
        "total_asset": 5000,
        "total_equity": 2000,
        "is_net_revenue": revenue,
        "is_shareholders_eat": net_income,
        "total_cfo": 180,
        "capex": -50,
        "ca_cce": 400,
        "cl_loan": 300,
        "cl_finlease": 20,
        "cl_due_long_debt": 30,
        "nl_loan": 500,
        "nl_finlease": 40,
        "is_net_business_profit": 160,
    }
    if quarter is not None:
        row["quarter"] = quarter
    return row


class DataCoreRawFundamentalTests(unittest.TestCase):
    def test_credentials_are_env_only(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(DataCoreRawFundamentalsError, "API key is not configured"):
                DataCoreCredentials.from_env()
        with patch.dict(os.environ, {"DATACORE_API_KEY": "dc-test"}, clear=True):
            self.assertEqual(DataCoreCredentials.from_env().api_key, "dc-test")

    def test_normalize_uses_only_statement_line_items_and_internal_shares(self):
        row = normalize_financial_row(
            raw_row(), period_type="ANNUAL", shares_by_ticker={"FPT": 100_000_000}
        )
        self.assertEqual(row.ticker, "FPT")
        self.assertEqual(row.period_end, "2025-12-31")
        self.assertEqual(row.period_type, "ANNUAL")
        self.assertEqual(row.capex, 50)
        self.assertEqual(row.total_debt, 890)
        self.assertEqual(row.shares_outstanding, 100_000_000)
        output = row.to_row()
        self.assertEqual(tuple(output), OUTPUT_FIELDS)
        for forbidden in (
            "score", "rank", "rating", "recommendation", "signal", "roe", "pe", "pb",
            "eps", "rvol", "fair_value", "mos", "buy_zone", "target", "risk_reward",
        ):
            self.assertNotIn(forbidden, output)

    def test_quarter_period_is_derived_only_from_raw_year_and_quarter(self):
        row = normalize_financial_row(
            raw_row(year=2026, quarter=2),
            period_type="QUARTER",
            shares_by_ticker={"FPT": 100},
        )
        self.assertEqual(row.period_end, "2026-06-30")

    def test_explicit_period_end_takes_priority(self):
        raw = raw_row(year=2025)
        raw["report_date"] = "2025-09-30"
        row = normalize_financial_row(raw, period_type="ANNUAL", shares_by_ticker={"FPT": 100})
        self.assertEqual(row.period_end, "2025-09-30")

    def test_non_hose_ticker_is_rejected(self):
        with self.assertRaisesRegex(DataCoreRawFundamentalsError, "outside HOSE security master"):
            normalize_financial_row(raw_row(symbol="AAA"), period_type="ANNUAL", shares_by_ticker={"FPT": 100})

    def test_missing_required_line_item_is_fail_closed(self):
        raw = raw_row()
        raw.pop("total_cfo")
        with self.assertRaisesRegex(DataCoreRawFundamentalsError, "operating_cash_flow"):
            normalize_financial_row(raw, period_type="ANNUAL", shares_by_ticker={"FPT": 100})

    def test_equity_and_assets_must_be_positive(self):
        raw = raw_row()
        raw["total_equity"] = 0
        with self.assertRaisesRegex(DataCoreRawFundamentalsError, "equity must be positive"):
            normalize_financial_row(raw, period_type="ANNUAL", shares_by_ticker={"FPT": 100})

    def test_direct_total_debt_is_allowed_as_raw_line_item(self):
        raw = raw_row()
        raw["total_debt"] = 777
        row = normalize_financial_row(raw, period_type="ANNUAL", shares_by_ticker={"FPT": 100})
        self.assertEqual(row.total_debt, 777)

    def test_reconcile_requires_two_annual_periods_for_every_hose_ticker(self):
        shares = {"FPT": 100, "HPG": 100}
        annual = [
            normalize_financial_row(raw_row("FPT", 2024), period_type="ANNUAL", shares_by_ticker=shares),
            normalize_financial_row(raw_row("FPT", 2025), period_type="ANNUAL", shares_by_ticker=shares),
            normalize_financial_row(raw_row("HPG", 2025), period_type="ANNUAL", shares_by_ticker=shares),
        ]
        with self.assertRaisesRegex(DataCoreRawFundamentalsError, "below StockRadar minimum"):
            reconcile_rows(annual, [], expected_tickers=shares)

    def test_conflicting_duplicate_is_rejected(self):
        shares = {"FPT": 100}
        a = normalize_financial_row(raw_row("FPT", 2025, revenue=1000), period_type="ANNUAL", shares_by_ticker=shares)
        b = normalize_financial_row(raw_row("FPT", 2025, revenue=1100), period_type="ANNUAL", shares_by_ticker=shares)
        with self.assertRaisesRegex(DataCoreRawFundamentalsError, "conflicting duplicate"):
            reconcile_rows([a, b], [], expected_tickers=shares, minimum_annual_periods=1)

    def test_acquire_fundamentals_uses_only_named_annual_and_quarterly_datasets(self):
        shares = {"FPT": 100}
        client = FakeClient(
            [raw_row("FPT", 2024), raw_row("FPT", 2025)],
            [raw_row("FPT", 2026, quarter=1), raw_row("FPT", 2026, quarter=2)],
        )
        rows = acquire_fundamentals(client=client, shares_by_ticker=shares)
        self.assertEqual({call[0] for call in client.calls}, {DATACORE_ANNUAL_DATASET, DATACORE_QUARTERLY_DATASET})
        self.assertEqual(len(rows), 4)

    def test_read_hose_shares_filters_non_hose(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "security_master.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["ticker", "exchange", "listed_shares"])
                writer.writeheader()
                writer.writerow({"ticker": "FPT", "exchange": "HOSE", "listed_shares": "100"})
                writer.writerow({"ticker": "AAA", "exchange": "HNX", "listed_shares": "100"})
            self.assertEqual(read_hose_shares(path), {"FPT": 100.0})

    def test_written_fundamentals_are_compatible_with_stockradar_raw_contract(self):
        shares = {"FPT": 100}
        rows = [
            normalize_financial_row(raw_row("FPT", 2024), period_type="ANNUAL", shares_by_ticker=shares),
            normalize_financial_row(raw_row("FPT", 2025), period_type="ANNUAL", shares_by_ticker=shares),
        ]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "fundamentals.csv"
            write_fundamentals(path, rows)
            header = path.read_text(encoding="utf-8").splitlines()[0]
            self.assertEqual(tuple(header.split(",")), OUTPUT_FIELDS)
            for forbidden in ("roe", "pe", "pb", "eps", "score", "rank", "recommendation", "target"):
                self.assertNotIn(forbidden, header.lower())


if __name__ == "__main__":
    unittest.main()
