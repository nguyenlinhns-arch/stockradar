from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase" / "migrations" / "20260904130000_make_free_stock_ai_10_per_vietnam_day.sql"
EDGE = ROOT / "supabase" / "functions" / "stock-ai" / "index.ts"
INJECTOR = ROOT / "scripts" / "inject_ai_assistant.py"
VERIFIER = ROOT / "scripts" / "verify_ai_assistant.py"
AUTH_STATE = ROOT / "website" / "assets" / "auth-state-v2.js"
PAID_NAV = ROOT / "website" / "assets" / "paid-nav-v1.js"
PAGES = ROOT / ".github" / "workflows" / "pages.yml"
FAST = ROOT / ".github" / "workflows" / "pages-fast-hotfix.yml"


class StockAiProductCenterTests(unittest.TestCase):
    def test_free_quota_is_ten_per_vietnam_calendar_day(self):
        sql = MIGRATION.read_text(encoding="utf-8")
        lowered = sql.lower()
        self.assertIn("('free', 'stock_ai', 10, 86400", lowered)
        self.assertIn("asia/ho_chi_minh", lowered)
        self.assertIn("date_trunc('day'", lowered)
        self.assertIn("00:00", sql)
        self.assertIn("reset_at", lowered)
        self.assertIn("to service_role", lowered)
        self.assertIn("from public, anon, authenticated", lowered)
        self.assertNotIn("grant execute on function public.consume_stockradar_api_quota(uuid, text) to authenticated", lowered)

    def test_free_ai_uses_same_decision_context_and_premium_gets_proactive_alert_rights(self):
        source = EDGE.read_text(encoding="utf-8")
        self.assertIn('const ACTIVE_TIERS = new Set(["FREE", "TRIAL", "PAID"])', source)
        self.assertIn('const PREMIUM_TIERS = new Set(["TRIAL", "PAID"])', source)
        self.assertIn('const actionContext = readyRows.map((row) => normalizeReport', source)
        self.assertIn('alert_enabled: PREMIUM_TIERS.has(tier) && row.alert_enabled === true', source)
        self.assertIn("Bạn đã dùng đủ 10 lượt StockRadar AI hôm nay", source)
        self.assertNotIn("redactForFree", source)

    def test_homepage_transform_places_ai_before_supporting_product_sections(self):
        source = INJECTOR.read_text(encoding="utf-8")
        for marker in (
            "data-stockradar-ai-center",
            'id="stockradar-ai"',
            "Hỏi StockRadar AI trước khi ra quyết định.",
            "10 lượt hỏi mỗi ngày",
            "email Action Alert chủ động",
            "data-stockradar-ai-inline",
            "Radar HOSE",
            "Khuyến nghị",
            "Hiệu quả",
            "sr-ai-nav-link",
            "auth-state-v2.js",
        ):
            self.assertIn(marker, source)
        self.assertIn("main_match.end()", source)
        self.assertIn("sr-ai-support-title", source)
        self.assertIn('output / "assets" / "auth-state-v2.js"', source)

    def test_browser_auth_state_is_shared_by_header_and_ai(self):
        auth_state = AUTH_STATE.read_text(encoding="utf-8")
        paid_nav = PAID_NAV.read_text(encoding="utf-8")

        for source in (auth_state, paid_nav):
            self.assertIn("const STORAGE_KEY = 'stockradar-auth'", source)
            self.assertIn("sb-${", source)
            self.assertIn("auth-token", source)
            self.assertIn("data-header-auth-actions", source)
            self.assertIn("Nâng Premium", source)
            self.assertIn("Đăng xuất", source)

        self.assertIn("Guest -> Free -> Premium", auth_state)
        self.assertIn("header.querySelectorAll('[data-auth-nav]').forEach(node => node.remove())", auth_state)
        self.assertIn("if (group.innerHTML !== html) group.innerHTML = html", auth_state)
        self.assertIn("if (group.innerHTML !== html) group.innerHTML = html", paid_nav)
        self.assertIn("replace(/\\bTRIAL\\b/g, 'Premium')", auth_state)
        self.assertIn("replace(/\\bPAID\\b/g, 'Premium')", auth_state)

    def test_ai_verifier_locks_primary_surface_and_single_h1(self):
        source = VERIFIER.read_text(encoding="utf-8")
        self.assertIn("AI-first", source)
        self.assertIn('home.count("<h1") != 1', source)
        self.assertIn("10 lượt hỏi mỗi ngày", source)
        self.assertIn("email Action Alert chủ động", source)
        self.assertIn("hom-nay/index.html", source)

    def test_both_pages_pipelines_run_ai_transform_after_method_scrub(self):
        for path in (PAGES, FAST):
            source = path.read_text(encoding="utf-8")
            self.assertIn("python scripts/strip_public_methods.py .pages-site", source)
            self.assertIn("python scripts/inject_ai_assistant.py .pages-site", source)
            self.assertIn("python scripts/verify_ai_assistant.py .pages-site", source)
            self.assertLess(
                source.index("python scripts/strip_public_methods.py .pages-site"),
                source.index("python scripts/inject_ai_assistant.py .pages-site"),
            )


if __name__ == "__main__":
    unittest.main()
