#!/usr/bin/env python3
"""Build the static StockRadar site that GitHub Pages can publish."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.stockradar.production_data import require_publishable_manifest


WEBSITE = ROOT / "website"
DEFAULT_OUTPUT = ROOT / ".pages-site"
AUTH_ENABLED = os.environ.get("STOCKRADAR_ENABLE_AUTH", "").strip().lower() in {"1", "true", "yes", "on"}
AUTH_ROUTES = {"signup", "dang-nhap", "dat-lai-mat-khau", "tai-khoan"}
PREMIUM_CLIENT_ROUTES = {"co-phieu"}
EXCLUDED_NAMES = {"server.py", "__pycache__", "kien-thuc", "demo1", "email", "theo-doi", "pro"}
AUTH_CONFIG_TAG = '<script src="assets/auth-config.js?v=20260905-auth8" defer></script>\n'
AUTH_STATE_TAG = '<script src="assets/auth-state-v2.js?v=20260905-auth8" defer></script>\n'
SUPABASE_TAG = '<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2" defer></script>\n'
PUBLIC_AUTH_HEAD = AUTH_CONFIG_TAG + AUTH_STATE_TAG
PREMIUM_CLIENT_HEAD = SUPABASE_TAG + AUTH_CONFIG_TAG + AUTH_STATE_TAG
FULL_AUTH_HEAD = """\
<link rel="stylesheet" href="assets/auth.css?v=20260903-auth7">
<link rel="stylesheet" href="assets/auth-extra.css?v=20260903-auth7">
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2" defer></script>
<script src="assets/auth-config.js?v=20260905-auth8" defer></script>
<script src="assets/auth-email-gate.js?v=20260903-auth7" defer></script>
<script src="assets/auth-policy.js?v=20260903-auth7" defer></script>
<script src="assets/auth-account-security.js?v=20260903-auth7" defer></script>
<script src="assets/auth.js?v=20260903-auth7" defer></script>
<script src="assets/auth-extra.js?v=20260903-auth7" defer></script>
<script src="assets/auth-delete-security.js?v=20260903-auth7" defer></script>
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
        "provider": "supabase", "supabaseUrl": url, "supabasePublishableKey": key,
        "configured": bool(url and key), "emailDeliveryReady": email_ready,
    }
    target = output / "assets" / "auth-config.js"
    target.write_text(
        "window.STOCKRADAR_AUTH_CONFIG = Object.freeze("
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ");\n",
        encoding="utf-8",
    )


def page_route(page: Path, output: Path) -> str:
    relative = page.resolve().relative_to(output.resolve())
    return relative.parts[0] if len(relative.parts) > 1 else ""


def inject_auth_bundle(source: str, page: Path, output: Path) -> str:
    if not AUTH_ENABLED:
        return source
    if "</head>" not in source:
        raise RuntimeError("HTML page has no closing head tag")

    route = page_route(page, output)
    if route in AUTH_ROUTES:
        if "assets/auth.js" in source:
            return source
        head = FULL_AUTH_HEAD
    else:
        parts: list[str] = []
        if route in PREMIUM_CLIENT_ROUTES and "@supabase/supabase-js" not in source:
            parts.append(SUPABASE_TAG)
        if "assets/auth-config.js" not in source:
            parts.append(AUTH_CONFIG_TAG)
        if "assets/auth-state-v2.js" not in source:
            parts.append(AUTH_STATE_TAG)
        head = "".join(parts)
        if not head:
            return source

    return source.replace("</head>", head + "</head>", 1)


def radar_items(output: Path) -> list[dict[str, object]]:
    payload = json.loads((output / "public" / "data" / "ticker-universe.json").read_text(encoding="utf-8"))
    items = payload.get("items")
    if not isinstance(items, list):
        raise RuntimeError("Radar ticker universe items must be a list")
    clean: list[dict[str, object]] = []
    seen: set[str] = set()
    for raw in items:
        if not isinstance(raw, dict):
            raise RuntimeError("Radar ticker item must be an object")
        ticker = str(raw.get("ticker") or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", ticker):
            raise RuntimeError(f"Invalid public Radar ticker: {ticker!r}")
        if str(raw.get("exchange") or "").strip().upper() != "HOSE":
            raise RuntimeError(f"Non-HOSE ticker cannot get a public stock route: {ticker}")
        if ticker in seen:
            raise RuntimeError(f"Duplicate public Radar ticker: {ticker}")
        seen.add(ticker)
        clean.append(raw)
    return clean


def generate_radar_ticker_pages(output: Path) -> tuple[str, ...]:
    """Generate shareable static routes only for the already-public Radar 30 list."""
    template = (output / "co-phieu" / "index.html").read_text(encoding="utf-8")
    tickers: list[str] = []
    for item in radar_items(output):
        ticker = str(item["ticker"]).upper()
        company = str(item.get("company_name") or "").strip()
        sector = str(item.get("sector") or "HOSE").strip()
        identity = f"{company} · {sector}" if company else sector
        title = f"{ticker} — Phân tích Free & Premium | StockRadar"
        description = (
            f"Phân tích {ticker} ({identity}) trên StockRadar: bản Free công khai và cấu trúc Premium chuyên sâu. "
            "Radar rà soát không đồng nghĩa khuyến nghị mua."
        )
        canonical = f"https://stockradar.vn/co-phieu/{ticker}/"
        safe_title = html.escape(title, quote=True)
        safe_description = html.escape(description, quote=True)
        safe_canonical = html.escape(canonical, quote=True)

        source = template.replace('<base href="../">', '<base href="../../">', 1)
        source = re.sub(r'<title>.*?</title>', f'<title>{safe_title}</title>', source, count=1, flags=re.DOTALL)
        source = re.sub(
            r'<meta\s+name="description"\s+content="[^"]*">',
            f'<meta name="description" content="{safe_description}">',
            source,
            count=1,
        )
        social = (
            f'<link rel="canonical" href="{safe_canonical}">\n'
            '<meta property="og:site_name" content="StockRadar">\n'
            '<meta property="og:type" content="website">\n'
            f'<meta property="og:title" content="{safe_title}">\n'
            f'<meta property="og:description" content="{safe_description}">\n'
            f'<meta property="og:url" content="{safe_canonical}">\n'
            '<meta name="twitter:card" content="summary">\n'
            f'<meta name="twitter:title" content="{safe_title}">\n'
            f'<meta name="twitter:description" content="{safe_description}">\n'
        )
        source = source.replace("</head>", social + "</head>", 1)
        source = source.replace(
            '<body data-proposition="stock-report">',
            f'<body data-proposition="stock-report" data-static-ticker="{ticker}">',
            1,
        )
        target = output / "co-phieu" / ticker / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
        tickers.append(ticker)

    home_path = output / "index.html"
    home = home_path.read_text(encoding="utf-8")
    for ticker in tickers:
        home = home.replace(f"co-phieu/?ticker={ticker}", f"co-phieu/{ticker}/")
    home_path.write_text(home, encoding="utf-8")
    return tuple(tickers)


def _payload_requests_production(payload: dict[str, object]) -> bool:
    status = str(payload.get("data_status") or payload.get("status") or "").strip().upper()
    return bool(
        payload.get("full_universe")
        or payload.get("is_top5_hose")
        or str(payload.get("recommendation_mode") or "").strip().upper() == "PRODUCTION_APPROVED"
        or (status and not status.startswith("BLOCKED"))
    )


def _payload_snapshot_id(payload: dict[str, object]) -> str | None:
    direct = str(payload.get("snapshot_id") or "").strip()
    if direct:
        return direct
    snapshot = payload.get("snapshot")
    if isinstance(snapshot, dict):
        nested = str(snapshot.get("snapshot_id") or "").strip()
        return nested or None
    return None


def enforce_production_data_gate(payloads: list[tuple[Path, dict[str, object]]]) -> None:
    production_payloads = [(path, payload) for path, payload in payloads if _payload_requests_production(payload)]
    if not production_payloads:
        return
    manifest = os.environ.get("STOCKRADAR_PRODUCTION_MANIFEST", "").strip()
    if not manifest:
        raise RuntimeError(
            "Production-looking public data requires STOCKRADAR_PRODUCTION_MANIFEST; refusing to publish without a validated data contract."
        )
    try:
        max_age_hours = float(os.environ.get("STOCKRADAR_PRODUCTION_MAX_AGE_HOURS", "6"))
    except ValueError as error:
        raise RuntimeError("STOCKRADAR_PRODUCTION_MAX_AGE_HOURS must be numeric") from error
    if max_age_hours <= 0:
        raise RuntimeError("STOCKRADAR_PRODUCTION_MAX_AGE_HOURS must be positive")
    result = require_publishable_manifest(manifest, max_age_seconds=int(max_age_hours * 3600))
    for path, payload in production_payloads:
        payload_snapshot_id = _payload_snapshot_id(payload)
        if payload_snapshot_id and payload_snapshot_id != result.snapshot_id:
            raise RuntimeError(f"Public payload snapshot does not match production manifest: {path}")


def build(output: Path) -> None:
    output = validate_output(output)
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(WEBSITE, output, ignore=ignore)
    write_auth_config(output)
    public_radar_tickers = generate_radar_ticker_pages(output)

    for page in output.rglob("*.html"):
        source = page.read_text(encoding="utf-8")
        source = source.replace('data-api-mode="auto"', 'data-api-mode="disabled"')
        source = inject_auth_bundle(source, page, output)
        if 'name="robots"' not in source:
            source = source.replace("<head>", '<head><meta name="robots" content="noindex,nofollow">', 1)
        page.write_text(source, encoding="utf-8")

    (output / ".nojekyll").write_text("", encoding="utf-8")

    required = [
        output / "index.html", output / "assets" / "app.js",
        output / "public" / "data" / "radar.json", output / "public" / "data" / "recommendations.json",
        output / "public" / "data" / "ticker-universe.json", output / "public" / "data" / "stock-reports.json",
        output / "public" / "data" / "today-changes.json", output / "public" / "data" / "recommendation-journal.json",
        output / "public" / "data" / "track-record.json", output / "track-record" / "index.html",
        output / "radar5" / "index.html", output / "breakout" / "index.html", output / "risk" / "index.html",
        output / "nganh" / "index.html", output / "phan-tich" / "index.html", output / "khuyen-nghi" / "index.html",
        output / "hieu-qua" / "index.html", output / "co-phieu" / "index.html", output / "kiem-tra-co-phieu" / "index.html",
        output / "thay-doi-hom-nay" / "index.html", output / "dieu-khoan" / "index.html",
        output / "quyen-rieng-tu" / "index.html", output / "404.html",
    ]
    required.extend(output / "co-phieu" / ticker / "index.html" for ticker in public_radar_tickers)
    if AUTH_ENABLED:
        required.extend([
            output / "assets" / "auth.css", output / "assets" / "auth-extra.css",
            output / "assets" / "auth-email-gate.js", output / "assets" / "auth-policy.js",
            output / "assets" / "auth-account-security.js", output / "assets" / "auth.js",
            output / "assets" / "auth-extra.js", output / "assets" / "auth-delete-security.js",
            output / "assets" / "auth-state-v2.js", output / "assets" / "auth-config.js", output / "signup" / "index.html",
            output / "dang-nhap" / "index.html", output / "dat-lai-mat-khau" / "index.html",
            output / "tai-khoan" / "index.html",
        ])
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"Missing Pages assets: {missing}")
    if (output / "server.py").exists():
        raise RuntimeError("The Python server must not be included in GitHub Pages")

    public_data = sorted((output / "public" / "data").glob("*.json"))
    parsed_payloads: list[tuple[Path, dict[str, object]]] = []
    for path in public_data:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise RuntimeError(f"Public data payload must be a JSON object: {path}")
        parsed_payloads.append((path, payload))
    enforce_production_data_gate(parsed_payloads)

    for path in [*public_data, output / "assets" / "app.js"]:
        source = path.read_text(encoding="utf-8").upper()
        for forbidden in ("DEMO", "MOCK", "MÔ PHỎNG", "FIXTURE"):
            if forbidden in source:
                raise RuntimeError(f"Publication-only artifact contains {forbidden}: {path}")


if __name__ == "__main__":
    build(parse_args().output)