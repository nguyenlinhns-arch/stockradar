from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TARGETS = (
    "website/assets/app.js",
    "website/assets/account-preferences.js",
    "website/assets/home-core-v1.js",
    "website/assets/stock-api-client.js",
    "website/assets/buyer-readiness-v1.js",
    "website/assets/public-copy-v7.js",
    "website/assets/free-stock-context-v1.js",
    "website/assets/direct-ticker-nav-v1.js",
    "website/assets/stock-page-context-v1.js",
)


class AlphanumericTickerWebSurfaceTests(unittest.TestCase):
    def test_alpha_only_ticker_regex_is_absent(self) -> None:
        for relative in TARGETS:
            with self.subTest(path=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertNotIn("/^[A-Z]{3}$/", text)

    def test_main_lookup_updates_html_pattern_at_runtime(self) -> None:
        text = (ROOT / "website/assets/app.js").read_text(encoding="utf-8")
        self.assertIn("[A-Za-z0-9]{3}", text)
        self.assertIn("enableAlphanumericTickerInputs();", text)


if __name__ == "__main__":
    unittest.main()
