from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class HomeWorkspaceV2Tests(unittest.TestCase):
    def read(self, path: str) -> str:
        return (ROOT / path).read_text(encoding="utf-8")

    def test_homepage_is_ai_workspace_not_long_saas_landing(self):
        home = self.read("website/index.html")
        for marker in (
            "home-workspace",
            "workspace-grid",
            "data-stockradar-ai-center",
            "today-card",
            "data-today-actions",
            "data-home-reco-table",
            "TOP CỔ PHIẾU",
            "KHUYẾN NGHỊ",
            "CỦA STOCKRADAR",
            "buyer-first-section",
            "proof-grid",
            "plan-row",
        ):
            self.assertIn(marker, home)
        self.assertLess(home.index("data-stockradar-ai-center"), home.index("data-home-reco-table"))
        self.assertLess(home.index("data-home-reco-table"), home.index("buyer-first-section"))
        self.assertEqual(home.count("<h1"), 1)

    def test_homepage_public_seo_is_opened_only_by_final_production_guard(self):
        home = self.read("website/index.html")
        guard = self.read("scripts/enforce_ai_registration_ctas.py")
        self.assertIn('name="robots" content="noindex,nofollow"', home)
        self.assertIn('rel="canonical" href="https://stockradar.vn/"', home)
        self.assertIn('property="og:title"', home)
        self.assertIn('index,follow,max-image-preview:large', guard)
        self.assertIn("enforce_homepage_seo", guard)
        self.assertIn("Final public homepage is still noindex", guard)

    def test_workspace_data_renderer_is_fail_closed(self):
        js = self.read("website/assets/home-workspace-v2.js")
        for marker in (
            "public/data/radar.json",
            "public/data/recommendations.json",
            "public/data/today-changes.json",
            "isBlocked",
            "table.hidden = true",
            "Chưa có cổ phiếu đạt điều kiện phát hành",
            "performance_summary",
            "normalizeHeaderActions",
            "dang-ky/?plan=free",
        ):
            self.assertIn(marker, js)
        for forbidden in ("Math.random", "demoTicker", "fakePrice"):
            self.assertNotIn(forbidden, js)

    def test_workspace_css_is_dense_and_responsive(self):
        css = self.read("website/assets/home-workspace-v2.css")
        for marker in (
            ".home-market-bar",
            ".workspace-grid",
            ".workspace-main",
            ".today-card",
            ".reco-table",
            ".decision-strip",
            ".proof-grid",
            ".plan-row",
            "@media(max-width:980px)",
            "@media(max-width:720px)",
            "@media(max-width:520px)",
        ):
            self.assertIn(marker, css)

    def test_homepage_simplifies_ai_opening_message_after_mount(self):
        js = self.read("website/assets/home-workspace-v2.js")
        self.assertIn("normalizeAiOpeningMessage", js)
        self.assertIn("Tôi là StockRadar AI. Nhập một mã HOSE", js)
        self.assertIn("nếu dữ liệu chưa đủ chuẩn", js)
        self.assertNotIn("4M/Payback · CANSLIM", js)
        self.assertNotIn("SEPA/VCP", js)

    def test_homepage_ai_resolves_account_before_prompting_for_signup(self):
        ai = self.read("website/assets/ai-center.js")
        budget = self.read("scripts/optimize_home_asset_budget_v1.py")
        for marker in (
            "const STORAGE_KEY = 'stockradar-auth'",
            "window.StockRadarAuthClient",
            "storageKey: STORAGE_KEY",
            "currentAccountTier",
            "normalizeTier",
            "PREMIUM · AI KHÔNG GIỚI HẠN · ACTION ALERT",
            "Premium · hỏi không giới hạn",
            "thanh-toan/?plan=premium",
            "Nâng Premium",
            "onAuthStateChange",
            "20260905-ai5",
        ):
            self.assertIn(marker, ai if marker != "20260905-ai5" else budget)
        self.assertNotIn("PAID · AI KHÔNG GIỚI HẠN", ai)
        self.assertNotIn("TRIAL · AI", ai)
        self.assertNotIn("Xem gói Paid", ai)


if __name__ == "__main__":
    unittest.main()
