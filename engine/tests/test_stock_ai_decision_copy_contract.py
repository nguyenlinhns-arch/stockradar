from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "supabase" / "functions" / "_shared" / "stockradar-core.ts"
AUTH_AI = ROOT / "supabase" / "functions" / "stock-ai" / "index.ts"
GUEST_AI = ROOT / "supabase" / "functions" / "stock-ai-guest" / "index.ts"


class StockAiDecisionCopyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = CORE.read_text(encoding="utf-8")
        cls.auth_ai = AUTH_AI.read_text(encoding="utf-8")
        cls.guest_ai = GUEST_AI.read_text(encoding="utf-8")

    def test_model_prompt_requires_decision_first_plain_text(self):
        source = self.source
        self.assertIn("CÁCH TRẢ LỜI — BẮT BUỘC", source)
        self.assertIn("dòng đầu tiên phải là “KẾT LUẬN: ...”", source)
        self.assertIn("Không dùng ký hiệu Markdown như **", source)
        self.assertIn("Không dùng thuật ngữ nội bộ “Action Gate”, “Data Gate”", source)
        self.assertIn("chưa có tín hiệu mua/bán được xác nhận", source)

    def test_current_internal_research_bundle_is_mapped(self):
        source = self.source
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
        self.assertIn("analysis: merge(rv7, quote, setup, scores, risk, market, p.analysis)", source)
        self.assertIn("scanner_postclose: merge(rv7, quote, setup, scores, risk, market, plan, p.scanner_postclose)", source)

    def test_research_answer_is_decision_first_and_rich(self):
        source = self.source
        self.assertIn("KẾT LUẬN: ${ticker} CHƯA MUA MỚI", source)
        self.assertIn("CẦN CHỜ:", source)
        self.assertIn("NẾU ĐANG NẮM GIỮ:", source)
        self.assertIn("VÌ SAO:", source)
        self.assertIn("GIÁ THAM KHẢO:", source)
        self.assertIn("TIN DOANH NGHIỆP:", source)
        self.assertIn("RỦI RO:", source)
        self.assertIn("Thông tin tham khảo từ dữ liệu ngày", source)
        self.assertIn("không liệt kê hàng loạt điểm số", source)
        self.assertIn("target_3_6m", source)
        self.assertIn("target_12m", source)

    def test_question_aware_fallback_covers_homepage_shortcuts(self):
        source = self.source
        self.assertIn("function questionIntent(question)", source)
        self.assertIn("return 'RISK'", source)
        self.assertIn("return 'MEDIUM'", source)
        self.assertIn("return 'LONG'", source)
        self.assertIn("return 'HOLD'", source)
        self.assertIn("return 'BUY'", source)
        self.assertIn("Rủi ro chính của ${ticker}", source)
        self.assertIn("${ticker} trong 3–6 tháng", source)
        self.assertIn("Nếu đang nắm giữ ${ticker}", source)
        self.assertIn("singleResearch(list[0], question)", source)

    def test_user_facing_state_and_block_reason_normalization_is_present(self):
        source = self.source
        self.assertIn("'THEO DOI KHONG HANH DONG': 'THEO DÕI — CHƯA HÀNH ĐỘNG'", source)
        self.assertIn("'HA TY TRONG HOAC BAN': 'HẠ TỶ TRỌNG HOẶC BÁN'", source)
        self.assertIn("'GIU QUAN SAT': 'GIỮ VÀ QUAN SÁT'", source)
        self.assertIn("'PHAN HOA THAN TRONG': 'PHÂN HÓA, THẬN TRỌNG'", source)
        self.assertIn("'LAGGING': 'YẾU HƠN THỊ TRƯỜNG'", source)
        self.assertIn("'WEAK': 'YẾU'", source)
        self.assertIn("'NEUTRAL': 'TRUNG TÍNH'", source)
        self.assertIn("NO_BUY_SETUP: 'giá và khối lượng chưa đáp ứng đủ điều kiện mua'", source)
        self.assertIn("RR_BELOW_2: 'lợi nhuận kỳ vọng chưa đạt gấp đôi khoản lỗ dự kiến'", source)

    def test_corporate_action_conflict_is_reconciled_before_showing_risk(self):
        source = self.source
        self.assertIn("corporateActionClear", source)
        self.assertIn("CURRENT_CORPORATE_ACTION_UNVERIFIED", source)
        self.assertIn("corp.execution_clear_v7 === true", source)
        self.assertIn("PASS_NO_NEAR_SENSITIVE_EVENT", source)

    def test_action_ready_fallback_uses_published_fields(self):
        source = self.source
        self.assertIn("function actionAnswer", source)
        self.assertIn("plan.buy_zone_low", source)
        self.assertIn("plan.stop_loss", source)
        self.assertIn("plan.target_near", source)
        self.assertIn("plan.risk_reward_to_base", source)

    def _assert_model_research_path(self, raw_source: str):
        source = "".join(raw_source.split())
        self.assertIn('if(mode==="METHOD_ONLY")', source)
        self.assertNotIn('if(mode!=="ACTION_READY")', source)
        self.assertIn('instructions:STOCKRADAR_SYSTEM_CORE', source)
        self.assertIn('answer_engine:modelText?"MODEL_PLUS_STOCKRADAR_CORE":"STOCKRADAR_CORE"', source)

    def test_signed_in_research_uses_model_when_data_exists(self):
        source = "".join(self.auth_ai.split())
        self._assert_model_research_path(self.auth_ai)
        self.assertIn('RESEARCH_CONTEXT:researchContexts', source)
        self.assertIn('question:message', source)

    def test_guest_research_uses_model_when_data_exists(self):
        source = "".join(self.guest_ai.split())
        self._assert_model_research_path(self.guest_ai)
        self.assertIn("RESEARCH_CONTEXT:query.scope==='ticker'?researchContext:contexts", source)
        self.assertIn('question:message', source)


if __name__ == "__main__":
    unittest.main()
