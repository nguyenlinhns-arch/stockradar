from pathlib import Path
import re


def replace_method(relative: str, name: str, new_block: str) -> None:
    path = Path(relative)
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(rf"^    def {re.escape(name)}.*?:\n.*?(?=^    def |^if __name__ ==)", re.M | re.S)
    match = pattern.search(text)
    if not match:
        raise SystemExit(f"method not found: {relative}:{name}")
    text = text[:match.start()] + new_block.rstrip() + "\n\n" + text[match.end():]
    path.write_text(text, encoding="utf-8")


replace_method(
    "engine/tests/test_buyer_first_product.py",
    "test_homepage_sells_decisions_before_methods",
    '''    def test_homepage_sells_decisions_before_methods(self) -> None:
        home = self.read("website/index.html")
        self.assertIn("StockRadar AI", home)
        self.assertIn("Hỏi một mã cổ phiếu", home)
        self.assertIn("mua được chưa", home)
        self.assertIn("đang nắm giữ nên làm gì", home)
        self.assertIn("rủi ro ở đâu", home)
        self.assertIn("data-stockradar-ai-center", home)
        self.assertIn("Hỏi không giới hạn", home)
        self.assertIn("Xem gói Paid", home)
        self.assertLess(home.index("Hỏi một mã cổ phiếu"), home.index("AI không thay thế hệ thống phân tích"))''',
)

replace_method(
    "engine/tests/test_conversion_v3.py",
    "test_homepage_becomes_lookup_first",
    '''    def test_homepage_becomes_lookup_first(self) -> None:
        transformed = MODULE.transform_home(self.read("website/index.html"))
        self.assertIn("StockRadar AI", transformed)
        self.assertIn("data-stockradar-ai-center", transformed)
        self.assertIn("Hỏi một mã cổ phiếu", transformed)
        self.assertIn('href="kiem-tra-co-phieu/"', transformed)
        self.assertIn('href="signup/?plan=free"', transformed)
        self.assertIn('href="dang-ky/?plan=premium"', transformed)
        self.assertNotIn("buyer-start-card", transformed)''',
)

replace_method(
    "engine/tests/test_direct_ticker_navigation.py",
    "test_primary_search_surfaces_exist",
    '''    def test_primary_search_surfaces_exist(self):
        homepage = (ROOT / "website" / "index.html").read_text(encoding="utf-8")
        self.assertIn("data-stockradar-ai-center", homepage)
        self.assertIn('href="kiem-tra-co-phieu/"', homepage)
        for relative in (
            "website/kiem-tra-co-phieu/index.html",
            "website/phan-tich/index.html",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("data-stock-search-form", source, relative)
            self.assertIn('name="ticker"', source, relative)''',
)

replace_method(
    "engine/tests/test_email_subscription_funnel.py",
    "test_homepage_source_still_routes_to_paid_conversion_and_public_lookup",
    '''    def test_homepage_source_still_routes_to_paid_conversion_and_public_lookup(self):
        home = self.read("website/index.html")
        self.assertIn("data-stockradar-ai-center", home)
        self.assertIn('href="kiem-tra-co-phieu/"', home)
        self.assertIn('href="signup/?plan=free"', home)
        self.assertIn('href="dang-ky/?plan=premium"', home)
        self.assertIn("Hỏi không giới hạn", home)
        self.assertIn("Action Alert", home)
        self.assertIn("3 câu/ngày", home)
        self.assertIn("10 câu/ngày", home)
        self.assertNotIn("FREE · EMAIL 09:00", home)
        self.assertNotIn("Nhận bản tin 09:00 miễn phí", home)
        self.assertNotIn("co-phieu/?ticker=", home)''',
)

replace_method(
    "engine/tests/test_homepage_asset_budget.py",
    "test_built_homepage_is_self_contained_while_radar_keeps_full_runtime",
    '''    def test_built_homepage_is_self_contained_while_radar_keeps_full_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "pages"
            build_pages.build(output)
            for page in sorted(output.rglob("*.html")):
                inject_public_ux.inject_page(page, output)

            home = (output / "index.html").read_text(encoding="utf-8")
            radar = (output / "radar5" / "index.html").read_text(encoding="utf-8")

            for heavy in (
                "public-ux.css", "public-ux.js", "public-fallbacks-v4.js", "direct-ticker-nav-v1.js",
                "auth-production-gate.js", "header-auth-dedupe-v6.js", "public-copy-v7.js",
                "assets/app.js", "home-dashboard.css", "site-v4.css",
            ):
                self.assertNotIn(heavy, home)
            for essential in ("home-core-v1.js", "mobile-touch-v1.css", "home-ai-center-v1.css", "ai-center.js"):
                self.assertIn(essential, home)
            self.assertIn("data-stockradar-ai-center", home)
            self.assertIn("Hỏi một mã cổ phiếu", home)

            for full in (
                "assets/app.js", "public-ux.css", "public-ux.js", "public-fallbacks-v4.js",
                "direct-ticker-nav-v1.js", "auth-production-gate.js", "header-auth-dedupe-v6.js", "public-copy-v7.js",
                "conversion-v1.css",
            ):
                self.assertIn(full, radar)
            self.assertIn("data-conversion-rail", radar)''',
)

replace_method(
    "engine/tests/test_paid_only_product_email_contract.py",
    "test_homepage_does_not_sell_product_email_as_free",
    '''    def test_homepage_does_not_sell_product_email_as_free(self):
        home = self.read("website/index.html")
        self.assertIn("FREE · 0Đ", home)
        self.assertIn("Không lưu danh mục cá nhân và không nhận email nội dung", home)
        self.assertIn("PAID", home)
        self.assertIn("Hỏi không giới hạn", home)
        self.assertIn("Action Alert", home)
        self.assertNotIn("FREE · EMAIL 09:00", home)
        self.assertNotIn("Nhận bản tin 09:00 miễn phí", home)
        self.assertNotIn("Nhận bản rà soát thị trường mỗi sáng", home)''',
)

replace_method(
    "engine/tests/test_static_assets.py",
    "test_professional_portal_shell_and_truthful_radar_workspace",
    '''    def test_professional_portal_shell_and_truthful_radar_workspace(self) -> None:
        homepage = (WEBSITE / "index.html").read_text(encoding="utf-8")
        radar = (WEBSITE / "radar5" / "index.html").read_text(encoding="utf-8")
        script = (WEBSITE / "assets" / "app.js").read_text(encoding="utf-8")
        styles = (WEBSITE / "assets" / "styles.css").read_text(encoding="utf-8")

        for expected in (
            "ai-home", "data-stockradar-ai-center", "Hỏi một mã cổ phiếu",
            "Chưa đăng nhập", "3 câu/ngày", "Free", "10 câu/ngày", "Paid",
            "Hỏi không giới hạn", 'href="radar5/"', 'href="kiem-tra-co-phieu/"',
        ):
            self.assertIn(expected, homepage)
        for expected in (
            "radar-workspace-grid", "data-radar-filter", "data-radar-table",
            "Radar toàn bộ cổ phiếu HOSE", "mỗi mã phải đi qua 8 lớp",
        ):
            self.assertIn(expected, radar)
        self.assertNotIn("co-phieu/?ticker=", homepage)
        self.assertNotIn("Radar 30", homepage)
        self.assertNotIn("30 mã", homepage)
        self.assertIn("portal-utility", script)
        self.assertIn("market-tape", script)
        self.assertIn("route.includes('/co-phieu/')", script)
        self.assertIn("Giá/OHLCV chưa kết nối", script)
        self.assertIn("dataReadinessMarkup", script)
        self.assertIn("BLOCKED_DATA_GATE", script)
        self.assertIn("data-radar-filter", script)
        self.assertIn("const stateLabels", script)
        self.assertIn(".market-tape", styles)''',
)

replace_method(
    "engine/tests/test_static_assets.py",
    "test_public_positioning_matches_current_horizons_and_pricing",
    '''    def test_public_positioning_matches_current_horizons_and_pricing(self) -> None:
        homepage = (WEBSITE / "index.html").read_text(encoding="utf-8")
        self.assertIn("StockRadar AI", homepage)
        self.assertIn("Hỏi một mã cổ phiếu", homepage)
        self.assertIn("mua được chưa", homepage)
        self.assertIn("đang nắm giữ nên làm gì", homepage)
        self.assertIn("rủi ro ở đâu", homepage)
        self.assertIn("3–6 tháng", homepage)
        self.assertIn("3 câu/ngày", homepage)
        self.assertIn("10 câu/ngày", homepage)
        self.assertIn("Hỏi không giới hạn", homepage)
        self.assertIn('href="dang-ky/?plan=premium"', homepage)
        self.assertNotIn("Radar 30", homepage)
        self.assertNotIn("30 mã", homepage)
        self.assertNotIn("10 ngành · 3 mã", homepage)
        self.assertNotIn("co-phieu/?ticker=", homepage)
        self.assertNotIn("DỮ LIỆU MẪU", homepage)
        self.assertNotIn("MẪU BÁO CÁO", homepage)
        self.assertNotIn("MẪU EMAIL", homepage)
        self.assertNotIn("199.000đ", homepage)
        self.assertNotIn("CHƯA MỞ BÁN", homepage)
        self.assertNotIn("đang hoàn thiện", homepage.lower())''',
)

replace_method(
    "engine/tests/test_static_radar_ticker_pages.py",
    "test_homepage_contains_no_fixed_ticker_links_before_or_after_build",
    '''    def test_homepage_contains_no_fixed_ticker_links_before_or_after_build(self):
        source_home = (ROOT / "website" / "index.html").read_text(encoding="utf-8")
        self.assertIn("data-stockradar-ai-center", source_home)
        self.assertIn('href="kiem-tra-co-phieu/"', source_home)
        self.assertNotIn("co-phieu/?ticker=", source_home)
        self.assertNotIn("Radar 30", source_home)

        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "site"
            build_pages.build(output)
            built_home = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("data-stockradar-ai-center", built_home)
            self.assertNotIn("co-phieu/?ticker=", built_home)
            self.assertNotIn("Radar 30", built_home)''',
)

for helper in (
    ".github/workflows/align-ai-homepage-regressions-once.yml",
    ".github/workflows/align-ai-homepage-regressions-v2-once.yml",
    "scripts/align_ai_homepage_regressions_once.py",
):
    Path(helper).unlink(missing_ok=True)
