from __future__ import annotations

import unittest

from stockradar.ticker_symbol import is_valid_hose_ticker, normalize_hose_ticker


class HoseTickerCompatibilityTests(unittest.TestCase):
    def test_valid_alpha_and_alphanumeric_hose_tickers(self) -> None:
        for ticker in ("FPT", "MBB", "C32", "HT1", "NT2", "PC1", "L10", "D2D"):
            with self.subTest(ticker=ticker):
                self.assertTrue(is_valid_hose_ticker(ticker))

    def test_normalization_preserves_digits(self) -> None:
        self.assertEqual(normalize_hose_ticker(" ht1 "), "HT1")
        self.assertEqual(normalize_hose_ticker("c32"), "C32")

    def test_invalid_symbols_are_rejected(self) -> None:
        for ticker in ("123", "AB", "ABCD", "A-1", "", None):
            with self.subTest(ticker=ticker):
                self.assertFalse(is_valid_hose_ticker(ticker))


if __name__ == "__main__":
    unittest.main()
