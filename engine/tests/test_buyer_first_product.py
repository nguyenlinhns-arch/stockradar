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
        self.assertIn("KHÔNG HÀNH ĐỘNG", home)
        self.assertIn("Trả phí cho lớp quyết định", home)

    def test_plan_page_defines_paid_output_not_just_features(self) -> None:
        plans = self.read("website/dang-ky/index.html")
        self.assertIn("buyer-plan-value", plans)
        self.assertIn("199K/30 ngày mua một lớp quyết định", plans)
        self.assertIn("Mua mới: MUA / CHỜ", plans)
        self.assertIn("Đang nắm giữ: GIỮ / NHỒI / HẠ TỶ TRỌNG / BÁN", plans)
        for field in ("Buy Zone", "Stop", "Target", "Risk/Reward", "Không tự gia hạn"):
            self.assertIn(field, plans)

    def test_plan_page_invites_proof_before_payment_and_states_limits(self) -> None:
        plans = self.read("website/dang-ky/index.html")
        self.assertIn("TRƯỚC KHI TRẢ TIỀN", plans)
        self.assertIn("Hãy tự kiểm chứng StockRadar trước khi nâng Premium", plans)
        for marker in (
            "Tra thử một mã", "Xem hiệu quả", "Xem tiêu chuẩn khuyến nghị",
            "không hứa real-time từng giây", "Không tự đặt lệnh", "không tự gia hạn",
        ):
            self.assertIn(marker, plans)
        self.assertIn('href="kiem-tra-co-phieu/"', plans)
        self.assertIn('href="hieu-qua/"', plans)
        self.assertIn('href="khuyen-nghi/"', plans)

    def test_stock_page_separates_new_position_and_holding_decisions(self) -> None:
        page = self.read("website/co-phieu/index.html")
        self.assertIn("Nếu chưa có hàng: MUA hay CHỜ?", page)
        self.assertIn("Nếu đang nắm giữ: GIỮ, NHỒI, HẠ TỶ TRỌNG hay BÁN?", page)
        self.assertIn("Kế hoạch giao dịch", page)
        self.assertIn("Buy Zone", page)
        self.assertIn("Stop-loss/điều kiện vô hiệu", page)
        self.assertIn("Risk/Reward", page)
        self.assertIn("Khi nào quyết định thay đổi?", page)

    def test_recommendation_page_exposes_audit_ready_signal_contract(self) -> None:
        page = self.read("website/khuyen-nghi/index.html")
        self.assertIn("TIÊU CHUẨN MỘT TÍN HIỆU TRẢ PHÍ", page)
        for field in (
            "Mã + snapshot", "Khung đầu tư", "Mua mới?", "Đang nắm giữ?",
            "Buy Zone", "Stop / vô hiệu", "Target", "Risk/Reward", "Trạng thái vòng đời",
        ):
            self.assertIn(field, page)
        self.assertIn("0 tín hiệu là một kết quả hợp lệ", page)

    def test_performance_page_proves_value_without_win_rate_cherry_pick(self) -> None:
        page = self.read("website/hieu-qua/index.html")
        self.assertIn("BẰNG CHỨNG TRƯỚC KHI TRẢ PHÍ", page)
        self.assertIn("Đừng chỉ nhìn tỷ lệ thắng", page)
        for marker in (
            "Số mẫu & trạng thái", "Lợi nhuận trung bình & trung vị", "Khoản lỗ & rủi ro",
            "So với VN-Index", "Dấu thời gian & nhật ký", "Không chạm Buy Zone → không tính như đã mua",
        ):
            self.assertIn(marker, page)

    def test_premium_email_contract_is_paid_decision_first_and_suppresses_noise(self) -> None:
        architecture = self.read("email/ARCHITECTURE.md")
        for marker in (
            "Free:",
            "Trial/Paid",
            "No material state change = no Action Alert",
            "What changed?",
            "Action map:",
            "What invalidates this?",
            "XEM TRẠNG THÁI MỚI NHẤT",
            "final preflight",
            "Idempotency-Key",
            "List-Unsubscribe",
            "ready_to_activate",
            "sending_enabled=false",
        ):
            self.assertIn(marker, architecture)
        for forbidden in ("4M", "CANSLIM", "SEPA/VCP", "VPA/RVOL", "Free/Trial/Paid"):
            self.assertNotIn(forbidden, architecture)

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
