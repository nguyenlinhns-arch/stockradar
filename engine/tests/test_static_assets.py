import struct
import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

from scripts import build_pages


ROOT = Path(__file__).resolve().parents[2]
WEBSITE = ROOT / "website"
class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references: list[str] = []
        self.base_href: str | None = None
        self.has_title = False
        self.has_description = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "title":
            self.has_title = True
        if tag == "meta" and values.get("name") == "description" and values.get("content"):
            self.has_description = True
        if tag == "base" and values.get("href"):
            self.base_href = values["href"]
        for key in (() if tag == "base" else ("href", "src")):
            if values.get(key):
                self.references.append(values[key])


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        if handle.read(8) != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"Not a PNG: {path}")
        length = struct.unpack(">I", handle.read(4))[0]
        chunk = handle.read(4)
        if chunk != b"IHDR" or length < 8:
            raise ValueError(f"Missing PNG IHDR: {path}")
        return struct.unpack(">II", handle.read(8))


class StaticAssetTests(unittest.TestCase):
    def test_html_pages_have_metadata_and_valid_internal_assets(self) -> None:
        for html in WEBSITE.rglob("index.html"):
            parser = AssetParser()
            parser.feed(html.read_text(encoding="utf-8"))
            self.assertTrue(parser.has_title, html)
            self.assertTrue(parser.has_description, html)
            for ref in parser.references:
                if urlparse(ref).scheme or ref.startswith(("mailto:", "tel:", "#")):
                    continue
                base_url = urljoin(html.as_uri(), parser.base_href or "")
                parsed = urlparse(urljoin(base_url, ref))
                path = Path(unquote(parsed.path))
                if parsed.path.endswith("/") or path.is_dir():
                    path /= "index.html"
                self.assertTrue(path.is_file(), f"{html}: missing {ref} -> {path}")

    def test_pages_build_is_static_and_truthful(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "pages"
            build_pages.build(output)
            self.assertTrue((output / ".nojekyll").is_file())
            self.assertFalse((output / "server.py").exists())
            for html in output.rglob("*.html"):
                source = html.read_text(encoding="utf-8")
                self.assertIn('data-api-mode="disabled"', source, html)
                self.assertIn('name="robots" content="noindex,nofollow"', source, html)
            for path in [*(output / "public" / "data").glob("*.json"), output / "assets" / "app.js"]:
                source = path.read_text(encoding="utf-8").upper()
                for forbidden in ("DEMO", "MOCK", "MÔ PHỎNG", "FIXTURE"):
                    self.assertNotIn(forbidden, source, path)

    def test_github_pages_workflow_runs_tests_before_deploy(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
        self.assertIn("python -m engine.cli build-public", workflow)
        self.assertNotIn("python -m engine.cli build-demo", workflow)
        self.assertIn("python -m unittest discover -s engine/tests -v", workflow)
        self.assertIn("python scripts/build_pages.py --output .pages-site", workflow)
        self.assertLess(workflow.index("Run regression suite"), workflow.index("Deploy to GitHub Pages"))

    def test_public_pages_do_not_use_old_personal_brand(self) -> None:
        for path in list(WEBSITE.rglob("*.html")) + list(WEBSITE.rglob("*.js")) + list(WEBSITE.rglob("*.css")):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("Linh", source, path)
            self.assertNotIn("Thầy", source, path)

    def test_knowledge_library_has_required_methods_and_sources(self) -> None:
        required = {
            "canslim-sepa": ("William J. O’Neil", "Mark Minervini"),
            "vpa": ("Anna Coulling", "Richard D. Wyckoff"),
            "4m": ("Phil Town", "Benjamin Graham"),
            "pocket-pivot": ("Gil Morales", "Chris Kacher"),
            "cong-cu-ky-thuat": ("John Bollinger", "Goichi Hosoda", "Stan Weinstein"),
            "quan-tri-rui-ro": ("Van K. Tharp", "Howard Marks"),
        }
        hub = (WEBSITE / "kien-thuc" / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-page-kind="knowledge-hub"', hub)
        for slug, sources in required.items():
            path = WEBSITE / "kien-thuc" / slug / "index.html"
            self.assertTrue(path.is_file(), slug)
            source = path.read_text(encoding="utf-8")
            self.assertIn('data-page-kind="method"', source)
            self.assertIn('id="stockradar"', source)
            self.assertIn('id="nguon"', source)
            for expected in sources:
                self.assertIn(expected, source, path)

        workflow = WEBSITE / "kien-thuc" / "quy-trinh-stockradar" / "index.html"
        self.assertTrue(workflow.is_file())
        source = workflow.read_text(encoding="utf-8")
        for expected in (
            "Bốn mục tiêu, bốn bộ điểm", "Score ≠ xác suất", "Không đếm trùng",
            "unknown = không mua", "10:30, 11:15, 13:30 và 14:15",
        ):
            self.assertIn(expected, source)

    def test_all_pages_have_accessible_mobile_navigation(self) -> None:
        for html in WEBSITE.rglob("index.html"):
            source = html.read_text(encoding="utf-8")
            self.assertIn('class="skip-link"', source, html)
            self.assertIn("data-nav-toggle", source, html)
            self.assertIn("data-nav-menu", source, html)

        for route in (
            "index.html", "radar5/index.html", "kiem-tra-co-phieu/index.html",
            "khuyen-nghi/index.html", "thay-doi-hom-nay/index.html",
            "hieu-qua/index.html", "nganh/index.html", "risk/index.html",
            "breakout/index.html", "track-record/index.html", "co-phieu/index.html",
        ):
            source = (WEBSITE / route).read_text(encoding="utf-8")
            self.assertNotIn('href="kien-thuc/', source, route)

    def test_professional_portal_shell_and_truthful_radar_workspace(self) -> None:
        homepage = (WEBSITE / "index.html").read_text(encoding="utf-8")
        radar = (WEBSITE / "radar5" / "index.html").read_text(encoding="utf-8")
        script = (WEBSITE / "assets" / "app.js").read_text(encoding="utf-8")
        styles = (WEBSITE / "assets" / "styles.css").read_text(encoding="utf-8")
        focus_styles = (WEBSITE / "assets" / "home-focus-v1.css").read_text(encoding="utf-8")

        for expected in (
            "operations-shell", "operations-search", "home-status-grid",
            "home-focus-grid", "home-radar-sector-list", "home-tier-grid",
            "Free bên trái · Premium bên phải", "30 mã",
        ):
            self.assertIn(expected, homepage)
        for expected in ("radar-workspace-grid", "data-radar-filter", "data-radar-table"):
            self.assertIn(expected, radar)
        for removed in ("BỘ NÃO STOCKRADAR", "TRUNG TÂM KIẾN THỨC", "KIẾN TRÚC 3 TẦNG"):
            self.assertNotIn(removed, homepage)
            self.assertNotIn(removed, radar)
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
        self.assertIn(".home-tier-grid", focus_styles)

    def test_master_product_surfaces_are_present_and_truthful(self) -> None:
        routes = {
            "nganh": "data-data-readiness", "phan-tich": "data-stock-search-form",
            "khuyen-nghi": "data-recommendations", "hieu-qua": "data-performance-summary",
            "co-phieu": "data-dynamic-stock-report", "radar5": "data-radar-table",
            "risk": "data-risk-alerts", "breakout": "data-radar-filter",
        }
        for route, marker in routes.items():
            source = (WEBSITE / route / "index.html").read_text(encoding="utf-8")
            self.assertIn(marker, source, route)

        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "pages"
            build_pages.build(output)
            for removed in ("kien-thuc", "email", "theo-doi", "tai-khoan", "signup", "pro"):
                self.assertFalse((output / removed).exists(), removed)

        recommendations = json.loads((WEBSITE / "public" / "data" / "recommendations.json").read_text(encoding="utf-8"))
        self.assertEqual(recommendations["data_status"], "BLOCKED_DATA_GATE")
        self.assertEqual(recommendations["items"], [])
        self.assertNotIn("is_mock", recommendations)

    def test_v2_recommendation_and_performance_surfaces(self) -> None:
        script = (WEBSITE / "assets" / "app.js").read_text(encoding="utf-8")
        recommendations_page = (WEBSITE / "khuyen-nghi" / "index.html").read_text(encoding="utf-8")
        performance_page = (WEBSITE / "hieu-qua" / "index.html").read_text(encoding="utf-8")
        report_page = (WEBSITE / "co-phieu" / "demo1" / "index.html").read_text(encoding="utf-8")
        for marker in (
            "CHƯA KÍCH HOẠT", "performance_entry_price", "final_return_pct",
            "benchmark_return_pct", "recommendation_list_view", "performance_view", "sample_premium_report_view",
        ):
            self.assertIn(marker, script)
        for marker in ("data-recommendation-filter", "data-recommendations", "NHẬT KÝ TRẠNG THÁI"):
            self.assertIn(marker, recommendations_page)
        self.assertIn("data-performance-summary", performance_page)
        self.assertIn("DATA GATE", performance_page)
        self.assertIn("BLOCKED_DATA_GATE", script)
        self.assertIn("data-stock-report", report_page)

        recommendations = json.loads((WEBSITE / "public" / "data" / "recommendations.json").read_text(encoding="utf-8"))
        self.assertEqual(recommendations["schema_version"], "2.1.2")
        self.assertEqual(recommendations["recommendation_mode"], "RESEARCH_ONLY")
        self.assertEqual(recommendations["data_status"], "BLOCKED_DATA_GATE")
        self.assertEqual(recommendations["items"], [])
        self.assertEqual(recommendations["performance_summary"]["total_published"], 0)
        self.assertIsNone(recommendations["performance_summary"]["win_rate_pct"])

    def test_required_v2_contract_documents_exist(self) -> None:
        names = (
            "STOCKRADAR_PRODUCT_SPEC_V2.md", "STOCKRADAR_BUILD_STATUS.md",
            "STOCKRADAR_RECOMMENDATION_SCHEMA.md", "STOCKRADAR_RECOMMENDATION_LIFECYCLE.md",
            "STOCKRADAR_PERFORMANCE_METHODOLOGY.md", "STOCKRADAR_TRACK_RECORD_SPEC.md",
            "STOCKRADAR_DATA_RIGHTS.md", "STOCKRADAR_EMAIL_SPEC.md",
            "STOCKRADAR_SUBSCRIPTION_SPEC.md", "STOCKRADAR_ANALYTICS_SPEC.md",
            "STOCKRADAR_ADS_EXPERIMENTS.md", "STOCKRADAR_COMPLIANCE_REVIEW.md",
            "STOCKRADAR_PERSONALIZATION_SPEC.md", "STOCKRADAR_TODAY_CHANGES_SPEC.md",
            "STOCKRADAR_RECOMMENDATION_JOURNAL_SPEC.md",
        )
        for name in names:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_public_state_vocabulary_and_backend_boundaries(self) -> None:
        script = (WEBSITE / "assets" / "app.js").read_text(encoding="utf-8")
        for label in (
            "THEO DÕI", "CHỜ MUA", "ĐẠT VÙNG MUA", "ĐANG CÓ HIỆU LỰC",
            "TĂNG QUÁ VÙNG MUA", "KHÔNG CÒN ĐẠT ĐIỀU KIỆN",
            "ĐẠT MỤC TIÊU", "CHẠM MỨC CẮT LỖ", "HẾT THỜI HẠN", "ĐÓNG KHUYẾN NGHỊ",
        ):
            self.assertIn(label, script)
        self.assertIn("Giá/OHLCV chưa kết nối", script)
        self.assertIn("public/data/recommendations.json", script)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "pages"
            build_pages.build(output)
            for route in ("email", "theo-doi", "tai-khoan", "signup", "pro", "kien-thuc"):
                self.assertFalse((output / route).exists(), route)

    def test_public_positioning_matches_current_horizons_and_pricing(self) -> None:
        homepage = (WEBSITE / "index.html").read_text(encoding="utf-8")
        for horizon in ("Ngắn hạn", "Trung hạn", "Dài hạn", "Tích sản"):
            self.assertIn(horizon, homepage)
        self.assertIn("BẢNG ĐIỀU HÀNH", homepage)
        self.assertIn("TRẠNG THÁI DỮ LIỆU", homepage)
        self.assertIn("Free bên trái · Premium bên phải", homepage)
        self.assertNotIn("DATA GATE", homepage)
        self.assertNotIn("DỮ LIỆU MẪU", homepage)
        self.assertNotIn("199.000đ", homepage)
        self.assertNotIn("CHƯA MỞ BÁN", homepage)

    def test_v212_lookup_dynamic_report_today_changes_and_journal_surfaces(self) -> None:
        required_pages = {
            "kiem-tra-co-phieu": "data-stock-search-form", "co-phieu": "data-dynamic-stock-report",
            "thay-doi-hom-nay": "data-today-changes",
        }
        for route, marker in required_pages.items():
            source = (WEBSITE / route / "index.html").read_text(encoding="utf-8")
            self.assertIn(marker, source)

        master = json.loads((WEBSITE / "public/data/ticker-universe.json").read_text(encoding="utf-8"))
        reports = json.loads((WEBSITE / "public/data/stock-reports.json").read_text(encoding="utf-8"))
        changes = json.loads((WEBSITE / "public/data/today-changes.json").read_text(encoding="utf-8"))
        journal = json.loads((WEBSITE / "public/data/recommendation-journal.json").read_text(encoding="utf-8"))
        self.assertFalse(master["full_universe"])
        self.assertEqual(master["public_scope"], "REFERENCE_ONLY")
        self.assertEqual(master["data_status"], "BLOCKED_DATA_GATE")
        reference = master["internal_reference"]
        self.assertEqual(reference["snapshot_id"], "hose-universe-2026-09-02-065632-vn")
        self.assertEqual(reference["record_count"], 405)
        self.assertEqual(reference["validated_count"], 405)
        self.assertFalse(reference["raw_publication_allowed"])
        self.assertFalse(reference["market_data_ready"])
        self.assertFalse(reference["ranking_ready"])
        self.assertLess(len(master["items"]), reference["record_count"])
        self.assertIn("VCI", {item["ticker"] for item in master["items"]})
        self.assertEqual(reports["data_status"], "BLOCKED_DATA_GATE")
        self.assertEqual(reports["items"], [])
        self.assertEqual(changes["data_status"], "BLOCKED_DATA_GATE")
        self.assertEqual(changes["items"], [])
        self.assertEqual(journal["data_status"], "BLOCKED_DATA_GATE")
        self.assertEqual(journal["items"], [])

        for path in (WEBSITE / "public" / "data").glob("*.json"):
            source = path.read_text(encoding="utf-8").upper()
            for forbidden in ("DEMO", "MOCK", "MÔ PHỎNG", "FIXTURE"):
                self.assertNotIn(forbidden, source, path)

        script = (WEBSITE / "assets/app.js").read_text(encoding="utf-8")
        for marker in (
            "ticker_input_started", "ticker_autocomplete_selected", "ticker_search_valid",
            "quick_report_view", "four_horizon_view", "holding_view", "today_changes_view",
            "loadDynamicStockReport", "recommendation-journal.json", "isValidStockTicker",
            "tickerAcceptedMarkup", "horizonCards", "sr_recent_tickers", "BLOCKED_DATA_GATE",
        ):
            self.assertIn(marker, script)

        for route in (
            "index.html", "radar5/index.html", "breakout/index.html", "risk/index.html",
            "track-record/index.html", "nganh/index.html", "phan-tich/index.html",
            "khuyen-nghi/index.html", "hieu-qua/index.html", "co-phieu/index.html",
            "kiem-tra-co-phieu/index.html", "thay-doi-hom-nay/index.html",
        ):
            source = (WEBSITE / route).read_text(encoding="utf-8")
            self.assertNotIn("DỮ LIỆU MẪU", source, route)
            self.assertNotIn("DEMO1", source, route)

    def test_six_creatives_have_feed_and_reels_variants(self) -> None:
        output = ROOT / "growth" / "creatives" / "output"
        feed = sorted(output.glob("*_feed_4x5.png"))
        reels = sorted(output.glob("*_reels_9x16.png"))
        self.assertEqual(len(feed), 6)
        self.assertEqual(len(reels), 6)
        self.assertTrue(all(png_dimensions(path) == (1080, 1350) for path in feed))
        self.assertTrue(all(png_dimensions(path) == (1080, 1920) for path in reels))


if __name__ == "__main__":
    unittest.main()
