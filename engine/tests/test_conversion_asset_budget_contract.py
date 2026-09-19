from pathlib import Path
import tempfile
import unittest

from scripts.optimize_conversion_asset_budget_v1 import ROUTES, process


class ConversionAssetBudgetContractTests(unittest.TestCase):
    def test_checkout_uses_shared_auth_state_instead_of_duplicate_paid_nav(self):
        config = ROUTES["thanh-toan"]
        self.assertIn("auth-state-v2.js", config["required_js"])
        self.assertIn("paid-nav-v1.js", config["remove_js"])
        self.assertNotIn("paid-nav-v1.js", config["required_js"])
        self.assertEqual(config["max_js"], 8)
        self.assertEqual(config["max_css"], 6)

    def test_checkout_pruner_removes_paid_nav_and_preserves_payment_runtime(self):
        config = ROUTES["thanh-toan"]
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            page_dir = output / "thanh-toan"
            assets = output / "assets"
            page_dir.mkdir(parents=True)
            assets.mkdir()

            css_names = sorted(config["required_css"])
            js_names = sorted(config["required_js"] | {"paid-nav-v1.js"})
            for name in css_names + js_names:
                (assets / name).write_text("/* fixture */\n", encoding="utf-8")

            links = "\n".join(f'<link rel="stylesheet" href="assets/{name}">' for name in css_names)
            scripts = "\n".join(f'<script src="assets/{name}"></script>' for name in js_names)
            page = f'''<!doctype html><html><head>{links}{scripts}</head><body>
            <img data-checkout-qr-image alt="VPBank 0934389822">
            <span data-checkout-reference>SR-TEST</span>
            <button data-checkout-confirm>Confirm</button>
            VPBank 0934389822
            </body></html>'''
            (page_dir / "index.html").write_text(page, encoding="utf-8")

            process(output, "thanh-toan", config)
            rendered = (page_dir / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("paid-nav-v1.js", rendered)
            self.assertIn("auth-state-v2.js", rendered)
            self.assertIn("checkout-v1.js", rendered)
            self.assertIn("data-checkout-confirm", rendered)

    def test_shared_auth_state_and_checkout_use_same_persistent_storage_key(self):
        root = Path(__file__).resolve().parents[2]
        auth_state = (root / "website" / "assets" / "auth-state-v2.js").read_text(encoding="utf-8")
        checkout = (root / "website" / "assets" / "checkout-v1.js").read_text(encoding="utf-8")
        self.assertIn("const STORAGE_KEY = 'stockradar-auth'", auth_state)
        self.assertIn("storageKey: 'stockradar-auth'", checkout)
        self.assertIn("persistSession: true", auth_state)
        self.assertIn("persistSession: true", checkout)


if __name__ == "__main__":
    unittest.main()
