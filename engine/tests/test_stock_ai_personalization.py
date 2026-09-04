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
        self.assertIn("cost_basis", source)
        self.assertIn("portfolio_weight_pct", source)
        self.assertIn('REQUEST_SCOPE: scope', source)
        self.assertIn('USER_CONTEXT: userContext', source)
        self.assertIn('scope === "portfolio"', source)
        self.assertIn("MAX_PORTFOLIO_TICKERS = 20", source)

    def test_single_ticker_context_is_minimized(self):
        source = EDGE.read_text(encoding="utf-8")
        self.assertIn('const requestedWatchItem = scope === "ticker"', source)
        self.assertIn('const userContext = scope === "portfolio"', source)
        self.assertIn('requested_ticker: requestedWatchItem ?', source)
        self.assertIn('requested_ticker_configured', source)
        self.assertIn('cost_basis: requestedWatchItem.cost_basis', source)
        self.assertIn('portfolio_weight_pct: requestedWatchItem.portfolio_weight_pct', source)
        self.assertIn('const researchTickers = scope === "ticker" ? [ticker]', source)
        self.assertNotIn("user.email", source)

    def test_position_context_is_optional_self_declared_and_cannot_infer_nav(self):
        source = EDGE.read_text(encoding="utf-8")
        self.assertIn('const ownsStock = row.owns_stock === true', source)
        self.assertIn('cost_basis: ownsStock ? positionNumber(row.cost_basis, 0.0001) : null', source)
        self.assertIn('portfolio_weight_pct: ownsStock ? positionNumber(row.portfolio_weight_pct, 0, 100) : null', source)
        self.assertIn('position_context_count: positionContextCount', source)
        self.assertIn('position_context_configured:', source)
        self.assertNotIn("broker_account", source)
        self.assertNotIn("position_quantity", source)
        self.assertNotIn("portfolio_nav", source)

    def test_free_and_premium_share_decision_context_while_alert_rights_differ(self):
        source = EDGE.read_text(encoding="utf-8")
        self.assertIn('const ACTIVE_TIERS = new Set(["FREE", "TRIAL", "PAID"])', source)
        self.assertIn('const PREMIUM_TIERS = new Set(["TRIAL", "PAID"])', source)
        self.assertIn('const actionContext = readyRows.map((row) => normalizeReport', source)
        self.assertIn('alert_enabled: PREMIUM_TIERS.has(tier) && row.alert_enabled === true', source)
        self.assertIn('tier === "FREE" ? "Bạn đã dùng đủ 10 lượt StockRadar AI hôm nay.', source)
        self.assertNotIn("redactForFree", source)
        self.assertNotIn("user.email", source)

    def test_browser_supports_inline_ai_ticker_and_portfolio_questions_without_secrets(self):
        source = CLIENT.read_text(encoding="utf-8")
        self.assertIn("portfolioIntent", source)
        self.assertIn("tickerForMessage", source)
        self.assertIn("if (portfolioIntent(text)) return '';", source)
        self.assertIn("requestScope", source)
        self.assertIn("Danh mục hôm nay", source)
        self.assertIn("mountInlineSurface", source)
        self.assertIn("data-stockradar-ai-inline", source)
        self.assertIn("Tạo Free · 10 lượt/ngày", source)
        self.assertIn("PREMIUM · AI + EMAIL ACTION ALERT", source)
        self.assertIn("Hỏi StockRadar AI", source)
        self.assertIn("scope,", source)
        self.assertNotIn("OPENAI_API_KEY", source)
        self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY", source)
        self.assertNotIn("service_role", source.lower())


if __name__ == "__main__":
    unittest.main()
