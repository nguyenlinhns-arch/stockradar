from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from engine.stockradar.ssi_raw_adapter import (
    SSICredentials,
    SSIRawAdapterError,
    SSIRawMarketAdapter,
    acquire_market_history,
    normalize_ohlcv,
    normalize_security,
    write_ohlcv,
    write_security_master,
)


@dataclass
class Security:
    symbol: str
    board: str = "HOSE"
    symbol_name_vi: str = "Doanh nghiệp"
    icb_code: str = "1000"
    icb_name: str = "Công nghiệp"
    listed_shares: int = 100_000_000
    first_trading_date: str = "2020/01/01"
    maturity_date: str = ""
    cw_underlying_symbol: str = ""


@dataclass
class Candle:
    symbol: str
    trading_date: str
    open_price: float = 10.0
    high_price: float = 11.0
    low_price: float = 9.5
    close_price: float = 10.5
    volume: int = 1_000_000
    value: float = 10_500_000.0


class FakeMarket:
    def __init__(self, securities=None, daily_pages=None, minute_pages=None):
        self.securities = securities or []
        self.daily_pages = daily_pages or {}
        self.minute_pages = minute_pages or {}
        self.calls = []

    def get_securities_info_by_board(self, board):
        self.calls.append(("securities", board))
        return self.securities

    def get_ohlc_1day_historical(self, symbol, from_date, to_date, page=1, size=1000):
        self.calls.append(("daily", symbol, page, size))
        return self.daily_pages.get((symbol, page), [])

    def get_ohlc_5minute_historical(self, symbol, from_date, to_date, page=1, size=1000):
        self.calls.append(("5m", symbol, page, size))
        return self.minute_pages.get((symbol, page), [])


class SSIRawAdapterTests(unittest.TestCase):
    def test_credentials_are_environment_only_and_missing_is_fail_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(SSIRawAdapterError, "credentials are not configured"):
                SSICredentials.from_env()
        values = {
            "SSI_FASTCONNECT_CLIENT_ID": "client",
            "SSI_FASTCONNECT_API_KEY": "key",
            "SSI_FASTCONNECT_API_SECRET": "secret-value",
        }
        with patch.dict(os.environ, values, clear=True):
            creds = SSICredentials.from_env()
            self.assertEqual(creds.client_id, "client")
            self.assertEqual(creds.api_key, "key")
            self.assertEqual(creds.api_secret, "secret-value")

    def test_security_normalization_uses_only_raw_identity_and_icb(self):
        row = normalize_security(Security(symbol="FPT", icb_name="Công nghệ"))
        self.assertEqual(row.ticker, "FPT")
        self.assertEqual(row.exchange, "HOSE")
        self.assertEqual(row.sector, "Công nghệ")
        exported = row.to_row()
        for forbidden in ("score", "rank", "rating", "recommendation", "signal", "roe", "pe", "rvol"):
            self.assertNotIn(forbidden, exported)

    def test_non_hose_and_missing_sector_are_rejected(self):
        with self.assertRaisesRegex(SSIRawAdapterError, "not HOSE"):
            normalize_security(Security(symbol="AAA", board="HNX"))
        with self.assertRaisesRegex(SSIRawAdapterError, "ICB sector is missing"):
            normalize_security(Security(symbol="AAA", icb_name=""))

    def test_common_stock_filter_excludes_warrant_and_non_three_letter_symbol(self):
        market = FakeMarket(securities=[
            Security(symbol="FPT", icb_name="Công nghệ"),
            Security(symbol="CFPT2401", cw_underlying_symbol="FPT", maturity_date="2027/01/01"),
            Security(symbol="FUEVFVND", icb_name="ETF"),
        ])
        adapter = SSIRawMarketAdapter(market)
        rows = adapter.fetch_hose_securities()
        self.assertEqual([row.ticker for row in rows], ["FPT"])

    def test_ohlcv_symbol_mismatch_is_rejected(self):
        with self.assertRaisesRegex(SSIRawAdapterError, "symbol mismatch"):
            normalize_ohlcv("FPT", Candle(symbol="HPG", trading_date="2026/09/03"))

    def test_ohlcv_invariants_are_checked(self):
        with self.assertRaisesRegex(SSIRawAdapterError, "high/low invariant"):
            normalize_ohlcv(
                "FPT",
                Candle(symbol="FPT", trading_date="2026/09/03", high_price=9.0, close_price=10.5),
            )
        with self.assertRaisesRegex(SSIRawAdapterError, "negative volume"):
            normalize_ohlcv(
                "FPT",
                Candle(symbol="FPT", trading_date="2026/09/03", volume=-1),
            )

    def test_daily_history_pages_until_short_page(self):
        page1 = [Candle("FPT", f"2026/01/{day:02d}") for day in range(1, 4)]
        page2 = [Candle("FPT", "2026/01/04")]
        market = FakeMarket(daily_pages={("FPT", 1): page1, ("FPT", 2): page2})
        adapter = SSIRawMarketAdapter(market)
        rows = adapter.fetch_daily_ohlcv("FPT", "2026-01-01", "2026-01-31", page_size=3)
        self.assertEqual(len(rows), 4)
        self.assertEqual([call[2] for call in market.calls if call[0] == "daily"], [1, 2])

    def test_duplicate_timestamp_is_rejected(self):
        market = FakeMarket(daily_pages={
            ("FPT", 1): [Candle("FPT", "2026/01/01"), Candle("FPT", "2026/01/01")]
        })
        adapter = SSIRawMarketAdapter(market)
        with self.assertRaisesRegex(SSIRawAdapterError, "duplicate SSI OHLCV timestamp"):
            adapter.fetch_daily_ohlcv("FPT", "2026-01-01", "2026-01-31")

    def test_retry_is_bounded_and_never_includes_secret(self):
        class BrokenMarket(FakeMarket):
            def get_securities_info_by_board(self, board):
                self.calls.append(("securities", board))
                raise RuntimeError("network failed secret-value")

        sleeps = []
        market = BrokenMarket()
        adapter = SSIRawMarketAdapter(
            market,
            retry_attempts=3,
            retry_delay_seconds=0.01,
            sleeper=sleeps.append,
        )
        with self.assertRaises(SSIRawAdapterError) as caught:
            adapter.fetch_hose_securities()
        self.assertEqual(len(market.calls), 3)
        self.assertEqual(len(sleeps), 2)
        self.assertNotIn("secret-value", str(caught.exception))

    def test_max_pages_fail_closed(self):
        market = FakeMarket(daily_pages={
            ("FPT", 1): [Candle("FPT", "2026/01/01")],
            ("FPT", 2): [Candle("FPT", "2026/01/02")],
        })
        adapter = SSIRawMarketAdapter(market)
        with self.assertRaisesRegex(SSIRawAdapterError, "paging exceeded max_pages"):
            adapter.fetch_daily_ohlcv(
                "FPT", "2026-01-01", "2026-01-31", page_size=1, max_pages=2
            )

    def test_acquisition_requires_stockradar_minimum_history(self):
        market = FakeMarket(
            securities=[Security(symbol="FPT", icb_name="Công nghệ")],
            daily_pages={("FPT", 1): [Candle("FPT", "2026/01/01")]},
        )
        adapter = SSIRawMarketAdapter(market)
        with self.assertRaisesRegex(SSIRawAdapterError, "coverage below StockRadar minimum"):
            acquire_market_history(
                adapter=adapter,
                from_date=date(2025, 1, 1),
                to_date=date(2026, 1, 1),
                minimum_daily_bars=210,
            )

    def test_csv_outputs_are_raw_only_and_pipeline_compatible(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            security = RawSecurityForTest()
            write_security_master(root / "security_master.csv", [security])
            write_ohlcv(root / "ohlcv.csv", [normalize_ohlcv("FPT", Candle("FPT", "2026/09/03"))])
            security_header = (root / "security_master.csv").read_text(encoding="utf-8").splitlines()[0]
            ohlcv_header = (root / "ohlcv.csv").read_text(encoding="utf-8").splitlines()[0]
            self.assertEqual(
                security_header,
                "ticker,name,exchange,sector,icb_code,listed_shares,first_trading_date",
            )
            self.assertEqual(ohlcv_header, "ticker,timestamp,open,high,low,close,volume,value")
            combined = (security_header + "," + ohlcv_header).lower()
            for forbidden in ("score", "rank", "recommendation", "signal", "rvol", "fair_value", "target"):
                self.assertNotIn(forbidden, combined)


class RawSecurityForTest:
    ticker = "FPT"
    name = "FPT"
    exchange = "HOSE"
    sector = "Công nghệ"
    icb_code = "9530"
    listed_shares = 100_000_000
    first_trading_date = "2006/12/13"

    def to_row(self):
        return {
            "ticker": self.ticker,
            "name": self.name,
            "exchange": self.exchange,
            "sector": self.sector,
            "icb_code": self.icb_code,
            "listed_shares": self.listed_shares,
            "first_trading_date": self.first_trading_date,
        }


if __name__ == "__main__":
    unittest.main()
