#!/usr/bin/env python3
"""Build the static StockRadar site that GitHub Pages can publish."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEBSITE = ROOT / "website"
DEFAULT_OUTPUT = ROOT / ".pages-site"
AUTH_ENABLED = os.environ.get("STOCKRADAR_ENABLE_AUTH", "").strip().lower() in {"1", "true", "yes", "on"}
AUTH_ROUTES = {"signup", "dang-nhap", "dat-lai-mat-khau", "tai-khoan"}
EXCLUDED_NAMES = {
    "server.py",
    "__pycache__",
    "kien-thuc",
    "demo1",
    "email",
    "theo-doi",
    "pro",
}
AUTH_HEAD = """\
<link rel="stylesheet" href="assets/auth.css?v=20260903-auth6">
<link rel="stylesheet" href="assets/auth-extra.css?v=20260903-auth6">
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2" defer></script>
<script src="assets/auth-config.js?v=20260903-auth6" defer></script>
<script src="assets/auth-email-gate.js?v=20260903-auth6" defer></script>
<script src="assets/auth-policy.js?v=20260903-auth6" defer></script>
<script src="assets/auth-account-security.js?v=20260903-auth6" defer></script>
<script src="assets/auth.js?v=20260903-auth6" defer></script>
<script src="assets/auth-extra.js?v=20260903-auth6" defer></script>
<script src="assets/auth-delete-security.js?v=20260903-auth6" defer></script>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def validate_output(output: Path) -> Path:
    resolved = output.resolve()
    if resolved in {ROOT.resolve(), WEBSITE.resolve(), Path(resolved.anchor)}:
        raise ValueError(f"Unsafe output directory: {resolved}")
    return resolved


def ignore(directory: str, names: list[str]) -> set[str]:
    excluded = {name for name in names if name in EXCLUDED_NAMES or name.endswith(".sqlite")}
    if Path(directory).resolve() == WEBSITE.resolve():
        if "data" in names:
            excluded.add("data")
        if not AUTH_ENABLED:
            excluded.update(name for name in AUTH_ROUTES if name in names)
    return excluded


def write_auth_config(output: Path) -> None:
    if not AUTH_ENABLED:
        return
    url = os.environ.get("STOCKRADAR_SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("STOCKRADAR_SUPABASE_PUBLISHABLE_KEY", "").strip()
    email_ready = os.environ.get("STOCKRADAR_AUTH_EMAIL_READY", "").strip().lower() in {"1", "true", "yes", "on"}
    if bool(url) != bool(key):
        raise RuntimeError("Supabase auth configuration is incomplete")
    if url and not url.startswith("https://"):
        raise RuntimeError("STOCKRADAR_SUPABASE_URL must use HTTPS")
    key_lower = key.lower()
    if key_lower.startswith("sb_secret_") or "service_role" in key_lower:
        raise RuntimeError("Refusing to publish a privileged Supabase key to GitHub Pages")

    payload = {
        "provider": "supabase",
        "supabaseUrl": url,
        "supabasePublishableKey": key,
        "configured": bool(url and key),
        "emailDeliveryReady": email_ready,
    }
    target = output / "assets" / "auth-config.js"
    target.write_text(
        "window.STOCKRADAR_AUTH_CONFIG = Object.freeze("
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ");\n",
        encoding="utf-8",
    )


def inject_auth_bundle(source: str) -> str:
    if not AUTH_ENABLED or "assets/auth.js" in source:
        return source
    if "</head>" not in source:
        raise RuntimeError("HTML page has no closing head tag")
    return source.replace("</head>", AUTH_HEAD + "</head>", 1)


def build(output: Path) -> None:
    output = validate_output(output)
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(WEBSITE, output, ignore=ignore)
    write_auth_config(output)

    for page in output.rglob("*.html"):
        source = page.read_text(encoding="utf-8")
        source = source.replace('data-api-mode="auto"', 'data-api-mode="disabled"')
        source = inject_auth_bundle(source)
        if 'name="robots"' not in source:
            source = source.replace(
                "<head>",
                '<head><meta name="robots" content="noindex,nofollow">',
                1,
            )
        page.write_text(source, encoding="utf-8")

    (output / ".nojekyll").write_text("", encoding="utf-8")

    required = [
        output / "index.html",
        output / "assets" / "app.js",
        output / "public" / "data" / "radar.json",
        output / "public" / "data" / "recommendations.json",
        output / "public" / "data" / "ticker-universe.json",
        output / "public" / "data" / "stock-reports.json",
        output / "public" / "data" / "today-changes.json",
        output / "public" / "data" / "recommendation-journal.json",
        output / "public" / "data" / "track-record.json",
        output / "track-record" / "index.html",
        output / "radar5" / "index.html",
        output / "breakout" / "index.html",
        output / "risk" / "index.html",
        output / "nganh" / "index.html",
        output / "phan-tich" / "index.html",
        output / "khuyen-nghi" / "index.html",
        output / "hieu-qua" / "index.html",
        output / "co-phieu" / "index.html",
        output / "kiem-tra-co-phieu" / "index.html",
        output / "thay-doi-hom-nay" / "index.html",
        output / "dieu-khoan" / "index.html",
        output / "quyen-rieng-tu" / "index.html",
        output / "404.html",
    ]
    if AUTH_ENABLED:
        required.extend([
            output / "assets" / "auth.css",
            output / "assets" / "auth-extra.css",
            output / "assets" / "auth-email-gate.js",
            output / "assets" / "auth-policy.js",
            output / "assets" / "auth-account-security.js",
            output / "assets" / "auth.js",
            output / "assets" / "auth-extra.js",
            output / "assets" / "auth-delete-security.js",
            output / "assets" / "auth-config.js",
            output / "signup" / "index.html",
            output / "dang-nhap" / "index.html",
            output / "dat-lai-mat-khau" / "index.html",
            output / "tai-khoan" / "index.html",
        ])
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"Missing Pages assets: {missing}")
    if (output / "server.py").exists():
        raise RuntimeError("The Python server must not be included in GitHub Pages")

    public_data = sorted((output / "public" / "data").glob("*.json"))
    for path in public_data:
        json.loads(path.read_text(encoding="utf-8"))
    for path in [*public_data, output / "assets" / "app.js"]:
        source = path.read_text(encoding="utf-8").upper()
        for forbidden in ("DEMO", "MOCK", "MÔ PHỎNG", "FIXTURE"):
            if forbidden in source:
                raise RuntimeError(f"Publication-only artifact contains {forbidden}: {path}")


if __name__ == "__main__":
    build(parse_args().output)
