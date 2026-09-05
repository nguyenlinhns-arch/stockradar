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
            "readableResearchFacts",
            "Giá trung bình 50 phiên",
            "Giá trung bình 200 phiên",
            "earlyVolumeText",
            "Vùng giá mua tham khảo",
            "Mức cắt lỗ",
            "Giá tham khảo 3–6 tháng",
            "Giá tham khảo 12 tháng",
            "Lợi nhuận kỳ vọng / khoản lỗ dự kiến",
            "ATR20",
            "Thị trường và ngành",
            "Tin doanh nghiệp chính thức",
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

    def test_model_output_appends_detail_only_when_requested(self):
        self.assertIn("!wantsResearchDetail(question)", VIEW.read_text(encoding="utf-8"))
        auth = AUTH.read_text(encoding="utf-8")
        guest = GUEST.read_text(encoding="utf-8")
        self.assertIn("appendResearchSnapshot(appendPosition(modelText", auth)
        self.assertIn("appendResearchSnapshot(modelText,researchContext,message,mode!=='ACTION_READY')", guest)


if __name__ == "__main__":
    unittest.main()
