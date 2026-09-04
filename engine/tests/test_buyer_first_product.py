from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WEBSITE = ROOT / "website"


class BuyerFirstProductTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_homepage_sells_decisions_before_methods(self) -> None:
        home = self.read("website/index.html")
        self.assertIn("buyer-first-section", home)
        self.assertIn("BẠN TRẢ TIỀN ĐỂ NHẬN GÌ?", home)
        self.assertIn("Mua mới hay chờ?", home)
        self.assertIn("Đang cầm thì làm gì?", home)
        self.assertIn("Hành động ở giá nào?", home)
        self.assertIn("Khi nào cần đổi quyết định?", home)
        self.assertIn("Không đủ chuẩn → không ép mua", home)
        self.assertIn("Trả phí cho lớp quyết định", home)
        self.assertIn("4M · CANSLIM · Payback", home)

    def test_plan_page_defines_paid_output_not_just_features(self) -> None:
        plans = self.read("website/dang-ky/index.html")
        self.assertIn("buyer-plan-value", plans)
        self.assertIn("199K/30 ngày mua một lớp quyết định", plans)
        self.assertIn("Mua mới: MUA / CHỜ", plans)
        self.assertIn("Đang nắm giữ: GIỮ / NHỒI / HẠ TỶ TRỌNG / BÁN", plans)
        for field in ("Buy Zone", "Stop", "Target", "Risk/Reward", "Không tự gia hạn"):
            self.assertIn(field, plans)

    def test_stock_page_separates_new_position_and_holding_decisions(self) -> None:
        page = self.read("website/co-phieu/index.html")
        self.assertIn("Nếu chưa có hàng: MUA hay CHỜ?", page)
        self.assertIn("Nếu đang nắm giữ: GIỮ, NHỒI, HẠ TỶ TRỌNG hay BÁN?", page)
        self.assertIn("Kế hoạch giao dịch", page)
        self.assertIn("Buy Zone", page)
        self.assertIn("Stop-loss/điều kiện vô hiệu", page)
        self.assertIn("Risk/Reward", page)
        self.assertIn("4M · Payback · CANSLIM", page)
        self.assertIn("Định giá Bear · Base · Bull", page)
        self.assertIn("SEPA · VCP · Stage · VPA", page)

    def test_recommendation_page_exposes_audit_ready_signal_contract(self) -> None:
        page = self.read("website/khuyen-nghi/index.html")
        self.assertIn("TIÊU CHUẨN MỘT TÍN HIỆU TRẢ PHÍ", page)
        for field in (
            "Mã + snapshot", "Khung đầu tư", "Mua mới?", "Đang nắm giữ?",
            "Buy Zone", "Stop / vô hiệu", "Target", "Risk/Reward", "Trạng thái vòng đời",
        ):
            self.assertIn(field, page)
        self.assertIn("0 tín hiệu là một kết quả hợp lệ", page)

    def test_buyer_first_css_is_responsive(self) -> None:
        css = self.read("website/assets/buyer-first-v1.css")
        self.assertIn(".buyer-first-grid", css)
        self.assertIn(".buyer-contract", css)
        self.assertIn(".buyer-plan-value-grid", css)
        self.assertIn(".buyer-recommendation-contract", css)
        self.assertIn("@media(max-width:900px)", css)
        self.assertIn("@media(max-width:620px)", css)


if __name__ == "__main__":
    unittest.main()
