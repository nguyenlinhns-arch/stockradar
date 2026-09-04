from pathlib import Path
import importlib.util
import unittest


ROOT = Path(__file__).resolve().parents[2]
HOME_SCRIPT_PATH = ROOT / "scripts" / "redesign_home_paid_intent_v1.py"
SPEC = importlib.util.spec_from_file_location("redesign_home_paid_intent_v1", HOME_SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class PaidOnlyEmailCopyTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_home_build_scrubs_free_product_email_promises(self):
        source = """
        <meta name="description" content="StockRadar — tra cứu cổ phiếu HOSE, nhận bản rà soát 09:00 miễn phí và dùng Premium để biết mua mới hay chờ, đang nắm giữ nên làm gì, vùng mua, stop, target và cảnh báo khi trạng thái thay đổi.">
        <span>FREE · EMAIL 09:00</span>
        <a>Nhận bản tin 09:00 miễn phí</a>
        <a>Xem bản rà soát Free</a>
        """
        transformed = MODULE.enforce_paid_only_email_copy(source)
        self.assertIn("Premium bổ sung báo cáo 09:00", transformed)
        self.assertIn("PREMIUM · EMAIL 09:00", transformed)
        self.assertIn("Xem email Premium 09:00", transformed)
        for forbidden in MODULE.BANNED_FREE_EMAIL_PROMISES:
            self.assertNotIn(forbidden.casefold(), transformed.casefold())

    def test_email_interest_edge_never_claims_free_product_email_entitlement(self):
        source = self.read("supabase/functions/email-interest/index.ts")
        self.assertIn("nhu cầu email Premium", source)
        self.assertIn("chưa tạo quyền gửi email", source)
        self.assertIn("tài khoản Trial/Paid", source)
        self.assertIn("delivery gate production", source)
        self.assertNotIn("tạo tài khoản Free và xác minh email để kích hoạt bản rà soát 09:00", source)

    def test_premium_lead_page_matches_runtime_entitlement(self):
        page = self.read("website/nhan-ban-tin/index.html")
        self.assertIn("PREMIUM · EMAIL THEO WATCHLIST", page)
        self.assertIn('data-next-href="signup/?plan=premium"', page)
        self.assertIn("Free chỉ nhận email hệ thống", page)
        self.assertNotIn("Nhận bản rà soát 09:00 miễn phí", page)


if __name__ == "__main__":
    unittest.main()
