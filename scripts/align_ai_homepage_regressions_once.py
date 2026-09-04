from pathlib import Path


def replace_once(relative: str, old: str, new: str) -> None:
    path = Path(relative)
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            return
        raise SystemExit(f"stale regression marker not found: {relative}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "engine/tests/test_email_subscription_funnel.py",
    '        self.assertEqual(payload["public_scope"], "REFERENCE_ONLY")\n',
    '        self.assertEqual(payload["public_scope"], "FAIL_CLOSED_NO_PUBLIC_TICKER_SEED")\n'
    '        self.assertEqual(payload["items"], [])\n',
)

replace_once(
    "engine/tests/test_static_assets.py",
    '        self.assertEqual(master["public_scope"], "REFERENCE_ONLY")\n',
    '        self.assertEqual(master["public_scope"], "FAIL_CLOSED_NO_PUBLIC_TICKER_SEED")\n',
)

replace_once(
    "engine/tests/test_static_assets.py",
    '        self.assertLess(len(master["items"]), reference["record_count"])\n'
    '        self.assertIn("VCI", {item["ticker"] for item in master["items"]})\n',
    '        self.assertEqual(master["items"], [])\n',
)

for helper in (
    ".github/workflows/align-ai-homepage-regressions-once.yml",
    ".github/workflows/align-ai-homepage-regressions-v2-once.yml",
    "scripts/align_ai_homepage_regressions_once.py",
):
    Path(helper).unlink(missing_ok=True)
