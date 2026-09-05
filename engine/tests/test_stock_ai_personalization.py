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
            ".from('profiles')",
            ".from('watchlist_items')",
            "owns_stock",
            "alert_enabled",
            "cost_basis",
            "portfolio_weight_pct",
        ):
            self.assertIn(marker, source)
        self.assertIn('REQUEST_SCOPE:scope', tight)
        self.assertIn('USER_CONTEXT:userContext', tight)
        self.assertIn("scope==='portfolio'", tight)
        self.assertIn('.limit(20)', tight)
        self.assertNotIn("user.email", source)

    def test_single_ticker_context_is_minimized(self):
        source = EDGE.read_text(encoding="utf-8")
        tight = compact(source)
        self.assertIn("requestedTickers=scope==='ticker'?[ticker]", tight)
        self.assertIn("scope==='ticker'?(contexts[0]||null):contexts", tight)
        self.assertIn("appendPosition(fallback,scope,ticker,watch)", tight)
        self.assertIn("watch.find(r=>r.ticker===ticker&&r.owns_stock)", tight)
        self.assertIn("cost_basis", source)
        self.assertIn("portfolio_weight_pct", source)
        self.assertNotIn("user.email", source)

    def test_position_context_is_optional_self_declared_and_cannot_infer_nav(self):
        source = EDGE.read_text(encoding="utf-8")
        tight = compact(source)
        self.assertIn("owns_stock:row.owns_stock===true", tight)
        self.assertIn("cost_basis:row.cost_basis==null?null:Number(row.cost_basis)", tight)
        self.assertIn("portfolio_weight_pct:row.portfolio_weight_pct==null?null:Number(row.portfolio_weight_pct)", tight)
        self.assertIn("watch.find(r=>r.ticker===ticker&&r.owns_stock)", tight)
        self.assertNotIn("broker_account", source)
        self.assertNotIn("position_quantity", source)
        self.assertNotIn("portfolio_nav", source)
        self.assertNotIn("portfolio_value", source)

    def test_free_and_premium_share_decision_context_while_proactive_rights_stay_outside_answer_redaction(self):
        source = EDGE.read_text(encoding="utf-8")
        tight = compact(source)
        self.assertIn('TIERS=newSet(["FREE","TRIAL","PAID"])', tight)
        self.assertIn("tier=String(profile?.account_tier", tight)
        self.assertIn("USER_CONTEXT:userContext", tight)
        self.assertIn("RESEARCH_CONTEXT:scope==='ticker'?(contexts[0]||null):contexts", tight)
        self.assertIn("Bạn đã dùng đủ 10 lượt StockRadar AI hôm nay.", source)
        self.assertNotIn("redactForFree", source)
        self.assertNotIn("user.email", source)
        # Proactive alert entitlement is enforced by the alert/email runtime, not by
        # degrading the AI answer context for Free users.
        self.assertNotIn("FREE_REDACTED", source)

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
