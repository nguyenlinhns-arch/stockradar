from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
EDGE = ROOT / "supabase" / "functions" / "stock-ai" / "index.ts"
CLIENT = ROOT / "website" / "assets" / "ai-assistant.js"


class StockAiPersonalizationTests(unittest.TestCase):
    def test_edge_reads_account_context_server_side(self):
        source = EDGE.read_text(encoding="utf-8")
        self.assertIn('.from("user_preferences")', source)
        self.assertIn('.from("watchlist_items")', source)
        self.assertIn("owns_stock", source)
        self.assertIn("alert_enabled", source)
        self.assertIn('REQUEST_SCOPE: scope', source)
        self.assertIn('USER_CONTEXT: userContext', source)
        self.assertIn('scope === "portfolio"', source)
        self.assertIn("MAX_PORTFOLIO_TICKERS = 20", source)

    def test_portfolio_mode_remains_fail_closed_and_free_redacted(self):
        source = EDGE.read_text(encoding="utf-8")
        self.assertIn("redactForFree", source)
        self.assertIn('tier === "FREE" ? redactForFree', source)
        self.assertIn("NO_READY_REPORT", source)
        self.assertIn("quota_consumed: false", source)
        self.assertIn("Không xếp hạng các score của các horizon khác nhau", source)
        self.assertNotIn("user.email", source)

    def test_browser_supports_ticker_and_portfolio_questions_without_secrets(self):
        source = CLIENT.read_text(encoding="utf-8")
        self.assertIn("portfolioIntent", source)
        self.assertIn("tickerForMessage", source)
        self.assertIn("if (portfolioIntent(text)) return '';", source)
        self.assertIn("requestScope", source)
        self.assertIn("Danh mục hôm nay", source)
        self.assertIn("Hỏi StockRadar AI", source)
        self.assertIn("scope,", source)
        self.assertNotIn("OPENAI_API_KEY", source)
        self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY", source)
        self.assertNotIn("service_role", source.lower())


if __name__ == "__main__":
    unittest.main()
