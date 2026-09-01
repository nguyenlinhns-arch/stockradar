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

    def test_github_pages_workflow_runs_tests_before_deploy(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
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
            "Bốn mục tiêu, bốn bộ điểm",
            "Score ≠ xác suất",
            "Không đếm trùng",
            "unknown = không mua",
            "10:30, 11:15, 13:30 và 14:15",
        ):
            self.assertIn(expected, source)

    def test_all_pages_have_accessible_mobile_navigation(self) -> None:
        for html in WEBSITE.rglob("index.html"):
            source = html.read_text(encoding="utf-8")
            self.assertIn('class="skip-link"', source, html)
            self.assertIn("data-nav-toggle", source, html)
            self.assertIn("data-nav-menu", source, html)
            self.assertIn('href="kien-thuc/"', source, html)

    def test_professional_portal_shell_and_truthful_radar_workspace(self) -> None:
        homepage = (WEBSITE / "index.html").read_text(encoding="utf-8")
        radar = (WEBSITE / "radar5" / "index.html").read_text(encoding="utf-8")
        script = (WEBSITE / "assets" / "app.js").read_text(encoding="utf-8")
        styles = (WEBSITE / "assets" / "styles.css").read_text(encoding="utf-8")

        for expected in ("dashboard-grid", "content-columns", "research-list", "sector-panel"):
            self.assertIn(expected, homepage)
        for expected in ("radar-workspace-grid", "truth-strip", "gate-grid"):
            self.assertIn(expected, radar)
        self.assertIn("Không phải dữ liệu cổ phiếu thật", radar)
        self.assertIn("Không dựng thứ hạng giả", homepage)
        self.assertIn("portal-utility", script)
        self.assertIn("market-tape", script)
        self.assertIn("route.includes('/co-phieu/')", script)
        self.assertIn("Chưa kết nối dữ liệu thị trường thật", script)
        self.assertIn("const stateLabels", script)
        self.assertIn(".market-tape", styles)
        self.assertIn(".radar-workspace", styles)

    def test_master_product_surfaces_are_present_and_truthful(self) -> None:
        routes = {
            "nganh": "DỮ LIỆU CHƯA ĐỦ ĐỂ XẾP HẠNG TOÀN HOSE",
            "phan-tich": "TICKER LOOKUP V2.1.2",
            "khuyen-nghi": "Công bố không đồng nghĩa đã mua",
            "hieu-qua": "Đếm đúng trước khi nói hiệu quả",
            "co-phieu/demo1": "KHÔNG PHẢI CỔ PHIẾU THẬT",
            "email": "10:30",
            "theo-doi": "CHƯA LƯU DỮ LIỆU NGƯỜI DÙNG",
            "tai-khoan": "CHƯA CÓ TÀI KHOẢN THẬT",
        }
        for route, marker in routes.items():
            source = (WEBSITE / route / "index.html").read_text(encoding="utf-8")
            self.assertIn(marker, source, route)

        homepage = (WEBSITE / "index.html").read_text(encoding="utf-8")
        for marker in ("BỘ NÃO STOCKRADAR", "04 · GATES", "score ≠ xác suất"):
            self.assertIn(marker, homepage)

        recommendations = json.loads(
            (WEBSITE / "public" / "data" / "recommendations.json").read_text(encoding="utf-8")
        )
        self.assertTrue(recommendations["is_mock"])
        self.assertIn("mô phỏng", recommendations["notice"])
        self.assertEqual(len(recommendations["items"]), 5)
        self.assertEqual(
            {item["horizon"] for item in recommendations["items"]},
            {"SHORT_TERM", "MEDIUM_TERM", "LONG_TERM", "ACCUMULATION"},
        )
        for item in recommendations["items"]:
            self.assertTrue(item["is_mock"])
            self.assertEqual(item["data_grade"], "MOCK")
            for field in ("recommendation_id", "snapshot_id", "thesis", "risks", "invalidation_conditions"):
                self.assertTrue(item[field], (item["ticker"], field))

    def test_v2_recommendation_and_performance_surfaces(self) -> None:
        script = (WEBSITE / "assets" / "app.js").read_text(encoding="utf-8")
        recommendations_page = (WEBSITE / "khuyen-nghi" / "index.html").read_text(encoding="utf-8")
        performance_page = (WEBSITE / "hieu-qua" / "index.html").read_text(encoding="utf-8")
        report_page = (WEBSITE / "co-phieu" / "demo1" / "index.html").read_text(encoding="utf-8")
        for marker in (
            "CHƯA KÍCH HOẠT", "performance_entry_price", "final_return_pct",
            "benchmark_return_pct", "recommendation_list_view", "performance_view",
            "sample_premium_report_view",
        ):
            self.assertIn(marker, script)
        for marker in ("data-recommendation-filter", "entry tính hiệu quả", "không có P/L"):
            self.assertIn(marker, recommendations_page)
        self.assertIn("data-performance-summary", performance_page)
        self.assertIn("SHADOW", performance_page)
        self.assertIn("Bốn góc nhìn", report_page)

        recommendations = json.loads(
            (WEBSITE / "public" / "data" / "recommendations.json").read_text(encoding="utf-8")
        )
        self.assertEqual(recommendations["schema_version"], "2.1.2")
        self.assertEqual(recommendations["recommendation_mode"], "RESEARCH_ONLY")
        unactivated = [item for item in recommendations["items"] if item["recommendation_state"] == "UNACTIVATED"]
        self.assertEqual(len(unactivated), 1)
        self.assertIsNone(unactivated[0]["performance_entry_price"])
        self.assertIsNone(unactivated[0]["current_return_pct"])
        closed = [item for item in recommendations["items"] if item["status"] == "CLOSED"]
        self.assertTrue(all(item["final_return_pct"] is not None for item in closed))
        self.assertTrue(all(item["current_return_pct"] is None for item in closed))

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
            "ĐẠT MỤC TIÊU", "CHẠM MỨC CẮT LỖ", "HẾT THỜI HẠN",
            "ĐÓNG KHUYẾN NGHỊ",
        ):
            self.assertIn(label, script)
        self.assertIn("Chưa kết nối dữ liệu thị trường thật", script)
        self.assertIn("public/data/recommendations.json", script)

        blocked_markers = {
            "email": "BLOCKED",
            "theo-doi": "BACKEND REQUIRED",
            "tai-khoan": "AUTH BLOCKED",
        }
        for route, marker in blocked_markers.items():
            source = (WEBSITE / route / "index.html").read_text(encoding="utf-8")
            self.assertIn(marker, source, route)

    def test_public_positioning_matches_current_horizons_and_pricing(self) -> None:
        homepage = (WEBSITE / "index.html").read_text(encoding="utf-8")
        pricing = (WEBSITE / "pro" / "index.html").read_text(encoding="utf-8")
        for horizon in ("Ngắn hạn", "Trung hạn", "Dài hạn", "Tích sản"):
            self.assertIn(horizon, homepage)
        self.assertIn("Top 10", homepage)
        self.assertIn("199.000đ", pricing)
        self.assertIn("299.000đ/30 ngày", pricing)

    def test_v212_lookup_dynamic_report_today_changes_and_journal_surfaces(self) -> None:
        required_pages = {
            "kiem-tra-co-phieu": "KIẾN TRÚC 3 TẦNG",
            "co-phieu": "Một mã, bốn góc nhìn",
            "thay-doi-hom-nay": "30–60 giây",
        }
        for route, marker in required_pages.items():
            source = (WEBSITE / route / "index.html").read_text(encoding="utf-8")
            self.assertIn(marker, source)

        master = json.loads((WEBSITE / "public/data/ticker-universe.json").read_text(encoding="utf-8"))
        reports = json.loads((WEBSITE / "public/data/stock-reports.json").read_text(encoding="utf-8"))
        changes = json.loads((WEBSITE / "public/data/today-changes.json").read_text(encoding="utf-8"))
        journal = json.loads((WEBSITE / "public/data/recommendation-journal.json").read_text(encoding="utf-8"))
        self.assertFalse(master["full_universe"])
        self.assertIn("VCI", {item["ticker"] for item in master["items"]})
        self.assertEqual(len(next(item for item in reports["items"] if item["ticker"] == "DEMO1")["horizon_views"]), 4)
        self.assertTrue(changes["items"])
        self.assertTrue(all(item["audit_reference"] for item in journal["items"]))

        script = (WEBSITE / "assets/app.js").read_text(encoding="utf-8")
        for marker in (
            "ticker_input_started", "ticker_autocomplete_selected", "ticker_search_valid",
            "quick_report_view", "four_horizon_view", "holding_view", "today_changes_view",
            "loadDynamicStockReport", "recommendation-journal.json",
        ):
            self.assertIn(marker, script)

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
