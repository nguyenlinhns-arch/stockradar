from pathlib import Path
import unittest

from scripts import redesign_home_paid_intent_v1


ROOT = Path(__file__).resolve().parents[2]


class HomePaidIntentV1Tests(unittest.TestCase):
    def test_home_paid_intent_moves_from_personal_value_to_proof_to_price(self) -> None:
        source = redesign_home_paid_intent_v1.SECTIONS
        ordered = (
            "SAU KHI TRA MÃ",
            "Đừng tự canh từng mã",
            "KIỂM CHỨNG TRƯỚC KHI TRẢ TIỀN",
            "Đừng tin lời quảng cáo. Hãy xem lịch sử.",
            "199.000đ",
            "Theo dõi mã của tôi",
        )
        positions = [source.index(marker) for marker in ordered]
        self.assertEqual(positions, sorted(positions))
        for marker in (
            "MUA / CHỜ",
            "GIỮ / TĂNG / GIẢM / BÁN",
            "Vùng mua · Stop · Target",
            "Có cả lãi và lỗ",
            "Không tính lệnh chưa kích hoạt",
            "So cùng VN-Index",
            "Không tự gia hạn",
            "Không cam kết lợi nhuận",
        ):
            self.assertIn(marker, source)
        for forbidden in ("DATA GATE", "manifest", "Full-Scan Gate", "Action Gate", "quality gate"):
            self.assertNotIn(forbidden, source)

    def test_home_paid_intent_personalizes_ticker_without_pii(self) -> None:
        source = (ROOT / "website" / "assets" / "home-paid-intent-v1.js").read_text(encoding="utf-8")
        for marker in (
            "data-home-intent-ticker",
            "data-premium-conversion-cta",
            "url.searchParams.set('ticker', value)",
            "sr_conversion_ticker_v1",
        ):
            self.assertIn(marker, source)
        for forbidden in ("email", "password", "otp", "broker_account", "nav_value"):
            self.assertNotIn(forbidden, source.lower())

    def test_home_paid_intent_css_is_responsive_and_hides_duplicate_hero_rows(self) -> None:
        source = (ROOT / "website" / "assets" / "home-paid-intent-v1.css").read_text(encoding="utf-8")
        self.assertIn("@media(max-width:900px)", source)
        self.assertIn("@media(max-width:640px)", source)
        self.assertIn(".app-home .home-value-strip,.app-home .operations-horizons{display:none!important}", source)
        self.assertIn("home-paid-intent-grid", source)
        self.assertIn("home-proof-grid", source)
        self.assertIn("home-premium-offer-card", source)


if __name__ == "__main__":
    unittest.main()
