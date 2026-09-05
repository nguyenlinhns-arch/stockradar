from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
VIEW = ROOT / "supabase" / "functions" / "_shared" / "stockradar-research-view.ts"
AUTH = ROOT / "supabase" / "functions" / "stock-ai" / "index.ts"
GUEST = ROOT / "supabase" / "functions" / "stock-ai-guest" / "index.ts"


class StockAiResearchSnapshotTests(unittest.TestCase):
    def test_snapshot_covers_decision_research_dimensions(self):
        source = VIEW.read_text(encoding="utf-8")
        for marker in (
            "DỮ LIỆU NGHIÊN CỨU STOCKRADAR",
            "buildResearchSnapshot",
            "appendResearchSnapshot",
            "Radar",
            "Cơ bản",
            "Định giá",
            "Kỹ thuật chi tiết",
            "Dòng tiền",
            "Cung/cầu",
            "Thanh khoản",
            "Pivot",
            "RVOL",
            "MA50",
            "MA200",
            "Pocket Pivot volume",
            "Buy Zone",
            "Stop",
            "Target 3–6 tháng",
            "Target 12 tháng",
            "R/R",
            "ATR20",
            "Market Direction",
            "Catalyst chính thức",
            "Chất lượng dữ liệu",
            "Điểm chặn hiện tại",
        ):
            self.assertIn(marker, source)

    def test_both_ai_endpoints_expose_and_append_research_data(self):
        for path in (AUTH, GUEST):
            source = path.read_text(encoding="utf-8")
            self.assertIn("stockradar-research-view.ts", source)
            self.assertIn("buildResearchSnapshot", source)
            self.assertIn("appendResearchSnapshot", source)
            self.assertIn("research_data", source)

    def test_model_output_cannot_suppress_research_snapshot(self):
        auth = AUTH.read_text(encoding="utf-8")
        guest = GUEST.read_text(encoding="utf-8")
        self.assertIn("appendResearchSnapshot(appendPosition(modelText", auth)
        self.assertIn("appendResearchSnapshot(modelText,researchContext)", guest)


if __name__ == "__main__":
    unittest.main()
