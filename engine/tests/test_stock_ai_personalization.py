from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
EDGE = ROOT / "supabase" / "functions" / "stock-ai" / "index.ts"
CLIENT = ROOT / "website" / "assets" / "ai-assistant.js"


def compact(source: str) -> str:
    """Ignore formatting/minification while preserving semantic contract checks."""
    return re.sub(r"\s+", "", source)


class StockAiPersonalizationTests(unittest.TestCase):
    def test_edge_reads_account_context_server_side(self):
        source = EDGE.read_text(encoding="utf-8")
        tight = compact(source)
        for marker in (
            '.from("user_preferences")',
            '.from("watchlist_items")',
            "owns_stock",
            "alert_enabled",
            "cost_basis",
            "portfolio_weight_pct",
        ):
            self.assertIn(marker, source)
        self.assertIn('REQUEST_SCOPE:scope', tight)
        self.assertIn('USER_CONTEXT:userContext', tight)
        self.assertIn('scope==="portfolio"', tight)
        self.assertIn('MAX_WATCH=20', tight)

    def test_single_ticker_context_is_minimized(self):
        source = EDGE.read_text(encoding="utf-8")
        tight = compact(source)
        self.assertIn('requested=scope==="ticker"?watch.find(x=>x.ticker===ticker)||null:null', tight)
        self.assertIn('userContext=scope==="portfolio"?', tight)
        self.assertIn('requested_ticker:requested', tight)
        self.assertIn('requested_ticker_configured:!!requested', tight)
        self.assertIn('cost_basis', source)
        self.assertIn('portfolio_weight_pct', source)
        self.assertIn('researchTickers=scope==="ticker"?[ticker]:', tight)
        self.assertNotIn("user.email", source)

    def test_position_context_is_optional_self_declared_and_cannot_infer_nav(self):
        source = EDGE.read_text(encoding="utf-8")
        tight = compact(source)
        self.assertIn('constown=r.owns_stock===true', tight)
        self.assertIn('cost_basis:own?pos(r.cost_basis,.0001):null', tight)
        self.assertIn('portfolio_weight_pct:own?pos(r.portfolio_weight_pct,0,100):null', tight)
        self.assertIn('position_context_count:positionCount', tight)
        self.assertIn('position_context_configured:', source)
        self.assertNotIn("broker_account", source)
        self.assertNotIn("position_quantity", source)
        self.assertNotIn("portfolio_nav", source)

    def test_free_and_premium_share_decision_context_while_alert_rights_differ(self):
        source = EDGE.read_text(encoding="utf-8")
        tight = compact(source)
        self.assertIn('TIERS=newSet(["FREE","TRIAL","PAID"])', tight)
        self.assertIn('PREMIUM=newSet(["TRIAL","PAID"])', tight)
        self.assertIn('action=ready.map(r=>normReport(r.data))', tight)
        self.assertIn('alert_enabled:PREMIUM.has(tier)&&r.alert_enabled===true', tight)
        self.assertIn("Bạn đã dùng đủ 10 lượt StockRadar AI hôm nay.", source)
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
