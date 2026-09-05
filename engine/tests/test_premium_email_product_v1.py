from datetime import datetime, timezone
from pathlib import Path
import unittest

from engine.stockradar.premium_email import build_premium_action_alert, build_premium_daily


ROOT = Path(__file__).resolve().parents[2]


class PremiumEmailProductV1Tests(unittest.TestCase):
    def test_action_alert_is_change_first_and_action_first(self) -> None:
        result = build_premium_action_alert({
            "ticker": "HPG",
            "horizon": "SHORT_TERM",
            "previous_state": "WAIT",
            "current_state": "BUY",
            "evaluated_at": "2026-09-04T10:30:00+07:00",
            "generated_at": "2026-09-04T10:31:00+07:00",
            "next_review": "11:15",
            "reference_price": 29100,
            "buy_zone": "28.8-29.3",
            "stop": 27.9,
            "target": 32.0,
            "risk_reward": 2.1,
            "invalidation": "Đóng dưới 27.9",
            "new_position_decision": "MUA",
            "holding_decision": "GIỮ / có thể TĂNG",
            "reasons": ["Giá vào vùng hành động", "Điều kiện xác nhận đã đạt"],
        })
        self.assertEqual(result["urgency"], "P2")
        self.assertEqual(result["subject"], "[MUA] HPG — 10:30 04/09/2026 — Giá 29.100đ")
        self.assertEqual(result["primary_cta"], "Phân tích chi tiết bằng AI StockRadar")
        self.assertIn("không mặc định đuổi giá", result["no_chase_notice"])
        self.assertEqual(result["decision_card"]["new_position_decision"], "MUA")
        self.assertEqual(result["decision_card"]["holding_decision"], "GIỮ / có thể TĂNG")

    def test_action_alert_rejects_noise_and_incomplete_buy(self) -> None:
        base = {
            "ticker": "FPT",
            "horizon": "SHORT_TERM",
            "previous_state": "HOLD",
            "current_state": "HOLD",
            "evaluated_at": datetime(2026, 9, 4, 10, 30, tzinfo=timezone.utc),
            "generated_at": datetime(2026, 9, 4, 10, 31, tzinfo=timezone.utc),
            "next_review": "11:15",
            "reference_price": 120,
            "invalidation": "Đóng dưới mốc bảo vệ",
            "reasons": ["Không có thay đổi quan trọng", "Rủi ro ổn định"],
        }
        with self.assertRaisesRegex(ValueError, "NO_MATERIAL_STATE_CHANGE"):
            build_premium_action_alert(base)

        buy = dict(base)
        buy.update(previous_state="WAIT", current_state="BUY")
        with self.assertRaisesRegex(ValueError, "buy_zone"):
            build_premium_action_alert(buy)

    def test_daily_is_watchlist_first_and_stable_is_a_valid_result(self) -> None:
        changed = build_premium_daily({
            "report_date": "2026-09-04T09:00:00+07:00",
            "generated_at": "2026-09-04T08:58:00+07:00",
            "market_context": "Trung tính",
            "stable_watchlist_count": 4,
            "watchlist_changes": [
                {"ticker": "VCI", "previous_state": "HOLD", "current_state": "REDUCE", "owns_stock": True},
                {"ticker": "HPG", "previous_state": "WAIT", "current_state": "BUY", "owns_stock": False},
            ],
        })
        self.assertEqual(changed["subject"], "[StockRadar] 2 mã cần chú ý hôm nay · 04/09")
        self.assertEqual(changed["watchlist_changes"][0]["ticker"], "VCI")
        self.assertEqual(changed["watchlist_changes"][0]["urgency"], "P1")
        self.assertEqual(changed["preheader"], "Watchlist của bạn trước, bối cảnh thị trường sau.")

        stable = build_premium_daily({
            "report_date": "2026-09-04T09:00:00+07:00",
            "generated_at": "2026-09-04T08:58:00+07:00",
            "market_context": "Trung tính",
            "stable_watchlist_count": 6,
            "watchlist_changes": [],
        })
        self.assertIn("Watchlist ổn định · chưa cần hành động", stable["subject"])
        self.assertEqual(stable["watchlist_changes"], [])

    def test_renderer_does_not_sell_named_methods(self) -> None:
        source = (ROOT / "engine" / "stockradar" / "premium_email.py").read_text(encoding="utf-8").upper()
        for term in ("CANSLIM", "SEPA", "VPA", "RVOL", "WYCKOFF", "MINERVINI"):
            self.assertNotIn(term, source)

    def test_health_rpc_is_user_scoped_and_metadata_only(self) -> None:
        sql = (ROOT / "supabase" / "migrations" / "20260904094800_add_my_email_delivery_health.sql").read_text(encoding="utf-8")
        self.assertIn("auth.uid()", sql)
        self.assertIn("delivery_system_ready", sql)
        self.assertIn("alert_ticker_count", sql)
        self.assertIn("last_delivery_status", sql)
        self.assertIn("grant execute on function public.get_my_stockradar_email_health_v1() to authenticated", sql)
        self.assertNotIn("provider_message_id", sql)
        self.assertNotIn("payload", sql)


if __name__ == "__main__":
    unittest.main()
