from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "supabase" / "functions" / "_shared" / "stockradar-core.ts"
AUTH_EDGE = ROOT / "supabase" / "functions" / "stock-ai" / "index.ts"
GUEST_EDGE = ROOT / "supabase" / "functions" / "stock-ai-guest" / "index.ts"


class StockAiResearchDataContractTests(unittest.TestCase):
    def test_core_always_builds_readable_research_snapshot(self):
        source = CORE.read_text(encoding="utf-8")
        for marker in (
            "DỮ LIỆU NGHIÊN CỨU STOCKRADAR",
            "export function researchSnapshot(c)",
            "export function researchSnapshotText(c)",
            "export function appendResearchData(answer, context)",
            "Radar",
            "Cơ bản",
            "Định giá",
            "Kỹ thuật",
            "Dòng tiền",
            "Cung/cầu",
            "Thanh khoản",
            "ATR20",
            "Target 3–6 tháng",
            "Target 12 tháng",
            "Catalyst chính thức",
            "Điểm chặn hiện tại",
        ):
            self.assertIn(marker, source)

    def test_authenticated_and_guest_ai_return_structured_research_data(self):
        for path in (AUTH_EDGE, GUEST_EDGE):
            source = path.read_text(encoding="utf-8")
            self.assertIn("appendResearchData", source)
            self.assertIn("researchSnapshot", source)
            self.assertIn("research_data", source)
            self.assertIn("RESEARCH_CONTEXT", source)

    def test_model_answer_cannot_drop_the_research_block(self):
        auth = AUTH_EDGE.read_text(encoding="utf-8")
        guest = GUEST_EDGE.read_text(encoding="utf-8")
        self.assertIn("appendResearchData(appendPosition(modelText", auth)
        self.assertIn("appendResearchData(modelText,context)", guest)


if __name__ == "__main__":
    unittest.main()
