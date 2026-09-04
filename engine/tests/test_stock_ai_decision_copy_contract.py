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
        self.assertIn("Góc nhìn nghiên cứu — chưa phải tín hiệu hành động đã được xác nhận.", source)

    def test_deterministic_research_answer_starts_with_actionable_conclusion(self):
        source = self.source
        conclusion = "KẾT LUẬN: ${ticker} CHƯA MUA MỚI"
        identity = "${ticker}: ${identityBits.join"
        self.assertIn(conclusion, source)
        self.assertIn(identity, source)
        self.assertLess(source.index(conclusion), source.index(identity))
        self.assertIn("MUA MỚI:", source)
        self.assertIn("NẾU ĐANG NẮM GIỮ:", source)
        self.assertIn("RỦI RO / ĐIỀU KIỆN ĐỔI:", source)
        self.assertIn("DỮ LIỆU:", source)

    def test_user_facing_state_normalization_is_present(self):
        source = self.source
        self.assertIn('.replace(/\\bWATCH\\b/gi, "THEO DÕI")', source)
        self.assertIn('.replace(/\\bTHEO DOI\\b/gi, "THEO DÕI")', source)
        self.assertIn('.replace(/\\bKHONG HANH DONG\\b/gi, "CHƯA HÀNH ĐỘNG")', source)

    def test_signed_in_research_uses_model_when_data_exists(self):
        source = self.auth_ai.replace(" ", "")
        self.assertIn('if(mode==="METHOD_ONLY")', source)
        self.assertNotIn('if(mode!=="ACTION_READY")', source)
        self.assertIn('RESEARCH_CONTEXT:researchContexts', source)
        self.assertIn('instructions:STOCKRADAR_SYSTEM_CORE', source)
        self.assertIn('answer_engine:"MODEL_PLUS_STOCKRADAR_CORE"', source)

    def test_guest_research_uses_model_when_data_exists(self):
        source = self.guest_ai.replace(" ", "")
        self.assertIn('if(mode==="METHOD_ONLY")', source)
        self.assertNotIn('if(mode!=="ACTION_READY")', source)
        self.assertIn('RESEARCH_CONTEXT:researchContext', source)
        self.assertIn('instructions:STOCKRADAR_SYSTEM_CORE', source)
        self.assertIn('answer_engine:"MODEL_PLUS_STOCKRADAR_CORE"', source)


if __name__ == "__main__":
    unittest.main()
