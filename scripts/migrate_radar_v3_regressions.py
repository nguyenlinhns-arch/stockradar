#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_function(path: Path, name: str, next_name: str, body: str) -> None:
    source = path.read_text(encoding="utf-8")
    start_marker = f"    def {name}(self):\n"
    end_marker = f"    def {next_name}(self):\n"
    if start_marker not in source or end_marker not in source:
        raise RuntimeError(f"Cannot locate {name} -> {next_name} in {path}")
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    source = source[:start] + body.rstrip() + "\n\n" + source[end:]
    path.write_text(source, encoding="utf-8")


def patch_email_tests() -> None:
    path = ROOT / "engine/tests/test_email_subscription_funnel.py"
    replace_function(
        path,
        "test_homepage_is_email_first_with_clear_paid_conversion",
        "test_home_and_global_conversion_state_skip_repeated_lead_cta",
        '''    def test_homepage_is_email_first_with_clear_paid_conversion(self):
        home = self.read("website/index.html")
        self.assertIn("data-email-conversion", home)
        self.assertIn("data-home-email-form", home)
        self.assertIn('id="nhan-ban-tin"', home)
        self.assertIn('href="thanh-toan/?plan=premium"', home)
        self.assertIn("home-radar-sector-list", home)
        self.assertIn("data-live-radar-home", home)
        self.assertIn("home-tier-grid", home)
        self.assertIn("Free và Premium có gì?", home)
        self.assertIn("Nhận bản rà soát thị trường mỗi sáng", home)
        self.assertIn("FREE 09:00", home)
        self.assertIn("199K", home)
        for feature in (
            "Radar HOSE", "Full HOSE → Full-Scan Gate → Ranking", "So sánh theo ngành",
            "Hiệu quả khuyến nghị", "Market/Sector", "VPA/RVOL",
            "Email & cảnh báo trong phiên",
        ):
            self.assertIn(feature, home)
        self.assertIn("4 mốc/ngày", home)
        self.assertIn("10:30 · 11:15 · 13:30 · 14:15", home)
        self.assertIn("Radar động theo snapshot", home)
        self.assertNotIn("Radar 30", home)
        self.assertNotIn("30 mã", home)
        self.assertNotIn("10 ngành · 3 mã", home)
        self.assertNotIn("co-phieu/?ticker=", home)
        self.assertIn("assets/home-focus-v1.css", home)
        self.assertIn("assets/home-conversion-v2.css", home)
        self.assertNotIn("assets/email-interest.js", home)
        self.assertNotIn("home-status-band", home)
        self.assertNotIn("home-status-grid", home)
        self.assertNotIn("assets/premium-preview-v7.css", home)
        self.assertNotIn("assets/home-dashboard.js", home)
        self.assertNotIn("home-watchlist-grid", home)
        self.assertNotIn("home-ticker-grid", home)
        self.assertNotIn("MẪU BÁO CÁO CHUYÊN SÂU", home)
        self.assertNotIn("MẪU EMAIL GÓI TRẢ PHÍ", home)
        self.assertNotIn("DỮ LIỆU MẪU", home)
        self.assertNotIn("MINH HỌA", home.upper())
        self.assertNotIn("đang hoàn thiện", home.lower())'''
    )
    replace_function(
        path,
        "test_radar_review_payload_is_30_tickers_10_sectors_3_each",
        "test_registration_page_compares_free_daily_and_premium_intraday",
        '''    def test_public_ticker_seed_is_fail_closed_until_full_hose_master_is_approved(self):
        payload = json.loads(self.read("website/public/data/ticker-universe.json"))
        self.assertEqual(payload["data_status"], "BLOCKED_DATA_GATE")
        self.assertEqual(payload["public_scope"], "FAIL_CLOSED_NO_PUBLIC_TICKER_SEED")
        self.assertEqual(payload["selection_kind"], "NONE_FAIL_CLOSED")
        self.assertEqual(payload["items"], [])
        self.assertEqual(payload["internal_reference"]["record_count"], 405)
        self.assertEqual(payload["internal_reference"]["validated_count"], 405)
        self.assertFalse(payload["internal_reference"]["raw_publication_allowed"])'''
    )
    replace_function(
        path,
        "test_recommendation_page_uses_30_stock_radar_review_list",
        "test_public_interest_client_calls_edge_without_privileged_secret",
        '''    def test_recommendation_page_uses_snapshot_bound_full_hose_radar(self):
        page = self.read("website/khuyen-nghi/index.html")
        self.assertIn("Tín hiệu hành động hiện tại", page)
        self.assertIn("0 mã", page)
        self.assertIn("Phạm vi quét", page)
        self.assertIn("Toàn HOSE", page)
        self.assertIn("Shortlist theo snapshot", page)
        self.assertIn("data-radar-review-list", page)
        self.assertIn("Không dùng mã mẫu hoặc danh sách lựa chọn thủ công", page)
        self.assertIn("Radar và Khuyến nghị là hai lớp khác nhau", page)
        self.assertNotIn("30 mã", page)
        self.assertNotIn("10 ngành · 3 mã", page)
        for ticker in ("ACB", "MBB", "HPG", "FPT", "VHM"):
            self.assertNotIn(f">{ticker}<", page)'''
    )


def patch_static_assets_tests() -> None:
    path = ROOT / "engine/tests/test_static_assets.py"
    replace_function(
        path,
        "test_professional_portal_shell_and_truthful_radar_workspace",
        "test_master_product_surfaces_are_present_and_truthful",
        '''    def test_professional_portal_shell_and_truthful_radar_workspace(self) -> None:
        homepage = (WEBSITE / "index.html").read_text(encoding="utf-8")
        radar = (WEBSITE / "radar5" / "index.html").read_text(encoding="utf-8")
        script = (WEBSITE / "assets" / "app.js").read_text(encoding="utf-8")
        styles = (WEBSITE / "assets" / "styles.css").read_text(encoding="utf-8")
        focus_styles = (WEBSITE / "assets" / "home-focus-v1.css").read_text(encoding="utf-8")

        for expected in (
            "operations-shell", "operations-search", "home-focus-grid", "home-radar-sector-list",
            "data-live-radar-home", "home-tier-grid", "Free và Premium có gì?", "Radar HOSE",
            "Full HOSE → Full-Scan Gate → Ranking", "Radar động theo snapshot",
        ):
            self.assertIn(expected, homepage)
        for expected in (
            "radar-workspace-grid", "data-radar-filter", "data-radar-table",
            "Radar toàn bộ cổ phiếu HOSE", "mỗi mã phải đi qua 8 lớp",
        ):
            self.assertIn(expected, radar)
        for removed in (
            "Radar 30", "30 mã", "10 ngành · 3 mã", "BỘ NÃO STOCKRADAR", "TRUNG TÂM KIẾN THỨC",
            "KIẾN TRÚC 3 TẦNG", "Free bên trái · Premium bên phải", "Trạng thái công khai",
            "Chưa có setup", "home-status-band", "home-status-grid",
        ):
            self.assertNotIn(removed, homepage)
        self.assertNotIn("co-phieu/?ticker=", homepage)
        self.assertNotIn("home-watchlist-grid", homepage)
        self.assertNotIn("home-ticker-grid", homepage)
        self.assertNotIn("premium-preview-section", homepage)
        self.assertIn("portal-utility", script)
        self.assertIn("market-tape", script)
        self.assertIn("route.includes('/co-phieu/')", script)
        self.assertIn("Giá/OHLCV chưa kết nối", script)
        self.assertIn("dataReadinessMarkup", script)
        self.assertIn("BLOCKED_DATA_GATE", script)
        self.assertIn("data-radar-filter", script)
        self.assertIn("const stateLabels", script)
        self.assertIn(".market-tape", styles)
        self.assertIn(".operations-status-grid", styles)
        self.assertIn(".home-radar-sector-row", focus_styles)
        self.assertIn(".home-tier-grid", focus_styles)'''
    )
    replace_function(
        path,
        "test_public_positioning_matches_current_horizons_and_pricing",
        "test_v212_lookup_dynamic_report_today_changes_and_journal_surfaces",
        '''    def test_public_positioning_matches_current_horizons_and_pricing(self) -> None:
        homepage = (WEBSITE / "index.html").read_text(encoding="utf-8")
        for horizon in ("Ngắn hạn", "Trung hạn", "Dài hạn", "Tích sản"):
            self.assertIn(horizon, homepage)
        self.assertIn("RA QUYẾT ĐỊNH TRÊN HOSE", homepage)
        self.assertIn('content="PRODUCTION"', homepage)
        self.assertIn("Free và Premium có gì?", homepage)
        self.assertIn("Radar HOSE", homepage)
        self.assertIn("Full HOSE → Full-Scan Gate → Ranking", homepage)
        self.assertIn("Radar động theo snapshot", homepage)
        self.assertNotIn("Radar 30", homepage)
        self.assertNotIn("30 mã", homepage)
        self.assertNotIn("10 ngành · 3 mã", homepage)
        self.assertNotIn("co-phieu/?ticker=", homepage)
        self.assertNotIn("home-status-band", homepage)
        self.assertNotIn("home-status-grid", homepage)
        self.assertNotIn("TRẠNG THÁI DỮ LIỆU", homepage)
        self.assertNotIn("DATA GATE", homepage)
        self.assertNotIn("DỮ LIỆU MẪU", homepage)
        self.assertNotIn("MẪU BÁO CÁO", homepage)
        self.assertNotIn("MẪU EMAIL", homepage)
        self.assertNotIn("199.000đ", homepage)
        self.assertNotIn("CHƯA MỞ BÁN", homepage)
        self.assertNotIn("đang hoàn thiện", homepage.lower())'''
    )


def main() -> None:
    patch_email_tests()
    patch_static_assets_tests()
    print("Radar V3 regression migration: PASS")


if __name__ == "__main__":
    main()
