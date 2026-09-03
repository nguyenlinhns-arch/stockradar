import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WEBSITE = ROOT / "website"


class AuthenticatedStockClientAssetTests(unittest.TestCase):
    def test_stock_page_loads_authenticated_api_client(self):
        page = (WEBSITE / "co-phieu" / "index.html").read_text(encoding="utf-8")
        self.assertIn("assets/stock-api.css", page)
        self.assertIn("assets/stock-api-client.js", page)
        self.assertIn("data-dynamic-stock-report", page)
        self.assertIn("data-premium-stock-report", page)
        self.assertIn("data-premium-gate-copy", page)
        self.assertIn("Phân tích cơ bản", page)
        self.assertIn("Phân tích chuyên sâu & kế hoạch hành động", page)

    def test_client_requires_session_and_routes_ready_report_to_premium_column(self):
        source = (WEBSITE / "assets" / "stock-api-client.js").read_text(encoding="utf-8")
        for marker in (
            "client.auth.getSession()",
            "session.access_token",
            "/functions/v1/stock-api",
            "Authorization: `Bearer ${auth.session.access_token}`",
            "if (!response.ok || payload.status !== 'READY') return false",
            "const premiumTarget = document.querySelector('[data-premium-stock-report]')",
            "const premiumGateCopy = document.querySelector('[data-premium-gate-copy]')",
            "liveContainer.hidden = false",
            "if (premiumGateCopy) premiumGateCopy.hidden = true",
            "if (response.status === 429)",
        ):
            self.assertIn(marker, source)
        self.assertNotIn("staticTarget.hidden = true", source)
        self.assertIn(
            "if (!response.ok || payload.status !== 'READY') return false;\n\n      const container = ensureLiveContainer();",
            source,
        )

    def test_probability_is_hidden_unless_calibrated_and_formatted_without_plus_sign(self):
        source = (WEBSITE / "assets" / "stock-api-client.js").read_text(encoding="utf-8")
        self.assertIn("payload.probability_calibrated === true", source)
        self.assertIn("formatProbability(payload.probability_pct)", source)
        self.assertIn("number < 0 || number > 100", source)
        self.assertIn("'KHÔNG CÔNG BỐ'", source)

    def test_client_does_not_embed_privileged_credentials(self):
        source = (WEBSITE / "assets" / "stock-api-client.js").read_text(encoding="utf-8").lower()
        for forbidden in ("service_role", "sb_secret_", "trading_token", "access_token:"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()