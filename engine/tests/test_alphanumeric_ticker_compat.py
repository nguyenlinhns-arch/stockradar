from __future__ import annotations

import unittest
from pathlib import Path

from engine.stockradar.ticker_symbol import is_valid_hose_ticker, normalize_hose_ticker


ROOT = Path(__file__).resolve().parents[2]


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

    def test_public_and_premium_clients_share_alphanumeric_contract(self) -> None:
        sources = [
            (ROOT / "website" / "assets" / "free-stock-context-v1.js").read_text(encoding="utf-8"),
            (ROOT / "website" / "assets" / "stock-page-context-v1.js").read_text(encoding="utf-8"),
            (ROOT / "website" / "assets" / "stock-api-client.js").read_text(encoding="utf-8"),
            (ROOT / "supabase" / "functions" / "stock-api" / "index.ts").read_text(encoding="utf-8"),
        ]
        for source in sources:
            with self.subTest(source=source[:40]):
                self.assertIn("^[A-Z0-9]{3}$", source)
                self.assertIn("/[A-Z]/", source)
                self.assertNotIn("^[A-Z]{3}$", source)


if __name__ == "__main__":
    unittest.main()
