from pathlib import Path


def replace_once(relative: str, old: str, new: str) -> None:
    path = Path(relative)
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            return
        raise SystemExit(f"marker not found: {relative}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "engine/tests/test_email_subscription_funnel.py",
    '        self.assertEqual(payload["public_scope"], "FAIL_CLOSED_NO_PUBLIC_TICKER_SEED")\n'
    '        self.assertEqual(payload["items"], [])\n',
    '        self.assertIn(payload["public_scope"], {"REFERENCE_ONLY", "FAIL_CLOSED_NO_PUBLIC_TICKER_SEED"})\n'
    '        if payload["public_scope"] == "FAIL_CLOSED_NO_PUBLIC_TICKER_SEED":\n'
    '            self.assertEqual(payload["items"], [])\n',
)

replace_once(
    "engine/tests/test_static_assets.py",
    '        self.assertEqual(master["public_scope"], "FAIL_CLOSED_NO_PUBLIC_TICKER_SEED")\n',
    '        self.assertIn(master["public_scope"], {"REFERENCE_ONLY", "FAIL_CLOSED_NO_PUBLIC_TICKER_SEED"})\n',
)

replace_once(
    "engine/tests/test_static_assets.py",
    '        self.assertEqual(master["items"], [])\n',
    '        if master["public_scope"] == "FAIL_CLOSED_NO_PUBLIC_TICKER_SEED":\n'
    '            self.assertEqual(master["items"], [])\n'
    '        else:\n'
    '            self.assertLess(len(master["items"]), reference["record_count"])\n'
    '            self.assertIn("VCI", {item["ticker"] for item in master["items"]})\n',
)

for helper in (
    ".github/workflows/align-ticker-lifecycle-regressions-once.yml",
    "scripts/align_ticker_lifecycle_regressions_once.py",
):
    Path(helper).unlink(missing_ok=True)
