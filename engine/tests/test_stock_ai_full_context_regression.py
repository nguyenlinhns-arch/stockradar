from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "supabase" / "functions" / "_shared" / "stockradar-core.ts"
AUTH = ROOT / "supabase" / "functions" / "stock-ai" / "index.ts"
GUEST = ROOT / "supabase" / "functions" / "stock-ai-guest" / "index.ts"


def compact(source: str) -> str:
    return re.sub(r"\s+", "", source)


class StockAiFullContextRegressionTests(unittest.TestCase):
    def test_core_keeps_reference_research_and_action_modes_fail_closed(self):
        source = CORE.read_text(encoding="utf-8")
        self.assertIn("if (actionReady) return 'ACTION_READY'", source)
        self.assertIn("if (researchReady) return 'RESEARCH_ONLY'", source)
        self.assertIn("if (referenceReady) return 'REFERENCE_ONLY'", source)
        self.assertIn("INTERNAL_REFERENCE_READY", source)
        self.assertIn("function actionAnswer", source)
        self.assertIn("chưa có tín hiệu mua/bán được xác nhận", source)
        self.assertIn("còn thiếu dữ liệu để đánh giá mua/bán", source)

    def test_authenticated_ai_combines_full_hose_context_with_published_action_reports(self):
        source = AUTH.read_text(encoding="utf-8")
        tight = compact(source)
        self.assertIn("loadResearchQuery(db,query)", source)
        self.assertIn("fetch_stockradar_ai_context", (ROOT / "supabase/functions/_shared/stockradar-query.ts").read_text(encoding="utf-8"))
        self.assertIn("fetch_stockradar_cached_report", source)
        self.assertIn("releasedReport(r.data,Date.now(),message)", source)
        self.assertIn("action=ready.filter(r=>r.horizon===horizon).map", source)
        self.assertIn("hasReference=contexts.length>0", tight)
        self.assertIn("stockRadarMode(action.length>0,hasResearch,hasReference)", tight)
        self.assertIn("MODEL_PLUS_STOCKRADAR_CORE", source)

    def test_authenticated_ai_minimizes_single_ticker_context_and_bounds_watchlist(self):
        source = AUTH.read_text(encoding="utf-8")
        tight = compact(source)
        self.assertIn(".from('watchlist_items')", source)
        self.assertIn(".limit(MAX_WATCH)", tight)
        self.assertIn("requestedTickers=query.tickers", tight)
        self.assertIn("RESEARCH_CONTEXT:scope==='ticker'?tickerContext:contexts", tight)
        self.assertIn("buildResearchSnapshot(tickerContext)", tight)
        self.assertIn("appendResearchSnapshot(fallback,tickerContext,message,mode!=='ACTION_READY')", tight)

    def test_guest_ai_keeps_three_question_quota_and_same_data_core(self):
        source = GUEST.read_text(encoding="utf-8")
        self.assertIn("loadResearchQuery(db,query)", source)
        self.assertIn("fetch_stockradar_ai_context", (ROOT / "supabase/functions/_shared/stockradar-query.ts").read_text(encoding="utf-8"))
        self.assertIn("fetch_stockradar_cached_report", source)
        self.assertIn("consume_stockradar_guest_ai_quota", source)
        self.assertIn("Đăng ký miễn phí để tiếp tục sử dụng AI StockRadar.", source)
        self.assertIn("MODEL_PLUS_STOCKRADAR_CORE", source)

    def test_research_v7_evidence_is_not_flattened_away(self):
        source = CORE.read_text(encoding="utf-8")
        for marker in (
            "p.research_v7",
            "p.quote",
            "p.setup",
            "p.scores",
            "p.risk",
            "p.market_context",
            "p.trade_plan",
            "p.catalyst",
            "p.corporate_action",
            "p.supply_institutional",
            "p.fundamental_valuation",
        ):
            self.assertIn(marker, source)


if __name__ == "__main__":
    unittest.main()
