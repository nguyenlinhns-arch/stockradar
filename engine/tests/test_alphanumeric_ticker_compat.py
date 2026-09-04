from __future__ import annotations

import unittest

from engine.stockradar.cache_publish import _normalize_ticker as cache_ticker
from engine.stockradar.datacore_raw_fundamentals import _ticker as datacore_ticker
from engine.stockradar.production_bundle import _normalized_ticker as bundle_ticker
from engine.stockradar.report_contract import _ticker as report_ticker
from engine.stockradar.ssi_raw_adapter import _is_common_stock, _ticker as ssi_ticker
from engine.stockradar.ticker_symbol import is_valid_hose_ticker, normalize_hose_ticker


class AlphanumericTickerCompatibilityTests(unittest.TestCase):
    def test_valid_hose_alphanumeric_symbols_are_accepted_end_to_end(self) -> None:
        for ticker in ("C32", "HT1", "NT2", "PC1", "L10", "D2D", "FPT", "MBB"):
            with self.subTest(ticker=ticker):
                self.assertTrue(is_valid_hose_ticker(ticker))
                self.assertEqual(cache_ticker(ticker), ticker)
                self.assertEqual(datacore_ticker(ticker), ticker)
                self.assertEqual(bundle_ticker(ticker), ticker)
                self.assertEqual(report_ticker(ticker), ticker)
                self.assertEqual(ssi_ticker(ticker), ticker)
                self.assertTrue(_is_common_stock({"symbol": ticker}))

    def test_normalization_preserves_digits(self) -> None:
        self.assertEqual(normalize_hose_ticker(" ht1 "), "HT1")
        self.assertEqual(normalize_hose_ticker("c32"), "C32")

    def test_pure_numeric_and_malformed_symbols_are_rejected(self) -> None:
        for ticker in ("123", "AB", "ABCD", "A-1", "", None):
            with self.subTest(ticker=ticker):
                self.assertFalse(is_valid_hose_ticker(ticker))


if __name__ == "__main__":
    unittest.main()
