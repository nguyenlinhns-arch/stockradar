#!/usr/bin/env python3
"""Prune obsolete final-artifact assets from My StockRadar and Hôm nay.

This runs after commercial reducers. It removes only route-irrelevant conversion,
buyer-readiness and generic fallback/ticker assets while preserving auth, dashboard,
email/watchlist, copy guard, shared auth state and notification runtimes.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import urlsplit
if __package__:
    from .optimize_home_asset_budget_v1 import minify_home_css
else:
    from optimize_home_asset_budget_v1 import minify_home_css

ROUTES = {
    "tai-khoan": {
        "remove_css": {
            "conversion-v1.css", "buyer-readiness-v1.css", "conversion-v3.css", "ai-assistant.css", "ai-decision-view.css",
        },
        "remove_js": {
            "buyer-readiness-v1.js", "conversion-v3.js", "ai-assistant.js", "ai-decision-view.js",
            "public-fallbacks-v4.js", "direct-ticker-nav-v1.js", "conversion-state-v1.js",
        },
        "required_assets": {
            "styles.css", "email-preferences.css", "account-notifications.css", "auth.css", "auth-extra.css",
            "professional-v5.css", "account-upgrade-v1.css", "public-ux.css", "site-v4.css",
            "mobile-touch-v1.css", "premium-email-product-v1.css", "commercial-v1.css", "header-notifications.css",
            "app.js", "account-preferences.js", "email-preferences.js", "account-notifications.js",
            "auth-config.js", "auth-email-gate.js", "auth-policy.js", "auth-account-security.js", "auth.js",
            "auth-extra.js", "auth-delete-security.js", "paid-nav-v1.js", "account-upgrade-v1.js", "public-ux.js",
            "auth-production-gate.js", "header-auth-dedupe-v6.js", "public-copy-v7.js",
            "decision-copy-guard-v1.js", "auth-state-v2.js", "commercial-v1.js", "header-notifications.js",
        },
        "required_html": {
            "data-product-email-preferences", "data-account-personalization", "data-account-watchlist-form",
        },
        "max_css": 13,
        "max_js": 22,
        "max_bytes": 365_000,
    },
    "hom-nay": {
        "remove_css": {"conversion-v1.css", "buyer-readiness-v1.css"},
        "remove_js": {
            "buyer-readiness-v1.js", "public-fallbacks-v4.js", "direct-ticker-nav-v1.js", "conversion-state-v1.js", "public-copy-v7.js",
        },
        "required_assets": {
            "ai-decision-view.css", "ai-decision-view.js",
            "styles.css", "auth.css", "auth-extra.css", "paid-dashboard-v1.css", "professional-v5.css",
            "public-ux.css", "site-v4.css", "mobile-touch-v1.css", "ai-assistant.css", "commercial-v1.css",
            "header-notifications.css", "app.js", "auth-config.js", "auth.js", "paid-dashboard-v1.js",
            "paid-nav-v1.js", "public-ux.js", "auth-production-gate.js", "header-auth-dedupe-v6.js",
            "decision-copy-guard-v1.js", "auth-state-v2.js", "ai-assistant.js",
            "commercial-v1.js", "header-notifications.js",
        },
        "required_html": {"data-paid-dashboard", "data-paid-actions", "data-paid-owned-list", "data-paid-watch-list"},
        "max_css": 12,
        "max_js": 16,
        "max_bytes": 325_000,
    },
}


def basename(ref: str) -> str:
    return Path(urlsplit(ref).path).name


def css_refs(source: str) -> list[str]:
    return re.findall(
        r'<link\b[^>]*rel=["\'][^"\']*stylesheet[^"\']*["\'][^>]*href=["\']([^"\']+)["\'][^>]*>',
        source,
        flags=re.I,
    )


def js_refs(source: str) -> list[str]:
    return re.findall(r'<script\b[^>]*src=["\']([^"\']+)["\'][^>]*>\s*</script>', source, flags=re.I | re.S)


def remove_asset(source: str, name: str, kind: str) -> str:
    if kind == "css":
        pattern = rf'\s*<link\b[^>]*href=["\'][^"\']*assets/{re.escape(name)}(?:\?[^"\']*)?["\'][^>]*>\s*'
    else:
        pattern = rf'\s*<script\b[^>]*src=["\'][^"\']*assets/{re.escape(name)}(?:\?[^"\']*)?["\'][^>]*>\s*</script>\s*'
    return re.sub(pattern, "\n", source, flags=re.I | re.S)


def local_size(output: Path, refs: list[str]) -> int:
    total = 0
    for ref in refs:
        if ref.startswith(("http://", "https://", "//")):
            continue
        target = output / "assets" / basename(ref)
        if not target.is_file():
            raise RuntimeError(f"Dashboard asset missing: {ref}")
        total += target.stat().st_size
    return total


def process(output: Path, route: str, cfg: dict) -> None:
    page = output / route / "index.html"
    if not page.is_file():
        raise RuntimeError(f"Dashboard page missing: {page}")
    source = page.read_text(encoding="utf-8")
    seen_scripts = set()
    def unique_script(match):
        ref = match.group(1)
        key = urlsplit(ref).path
        if key in seen_scripts:
            return ''
        seen_scripts.add(key)
        return match.group(0)
    source = re.sub(r'<script\b[^>]*src=["\']([^"\']+)["\'][^>]*>\s*</script>', unique_script, source, flags=re.I)

    for name in cfg["remove_css"]:
        source = remove_asset(source, name, "css")
    for name in cfg["remove_js"]:
        source = remove_asset(source, name, "js")
    page.write_text(source, encoding="utf-8")

    rendered = page.read_text(encoding="utf-8")
    css = css_refs(rendered)
    minify_home_css(output, css)
    js = js_refs(rendered)
    names = {
        basename(ref) for ref in css + js
        if not ref.startswith(("http://", "https://", "//"))
    }

    removed = cfg["remove_css"] | cfg["remove_js"]
    survived = names & removed
    if survived:
        raise RuntimeError(f"Obsolete dashboard assets survived on {route}: {sorted(survived)}")

    missing = cfg["required_assets"] - names
    if missing:
        raise RuntimeError(f"Required dashboard assets missing on {route}: {sorted(missing)}")

    for marker in cfg["required_html"]:
        if marker not in rendered:
            raise RuntimeError(f"Dashboard functional marker missing on {route}: {marker}")

    local_css = [ref for ref in css if not ref.startswith(("http://", "https://", "//"))]
    local_js = [ref for ref in js if not ref.startswith(("http://", "https://", "//"))]
    if len(local_css) > cfg["max_css"]:
        raise RuntimeError(f"Dashboard CSS budget exceeded on {route}: {len(local_css)} > {cfg['max_css']}")
    if len(local_js) > cfg["max_js"]:
        raise RuntimeError(f"Dashboard JS budget exceeded on {route}: {len(local_js)} > {cfg['max_js']}")

    total = local_size(output, css) + local_size(output, js)
    if total > cfg["max_bytes"]:
        raise RuntimeError(f"Dashboard byte budget exceeded on {route}: {total} > {cfg['max_bytes']}")

    print(f"Dashboard asset budget: PASS {route} ({len(local_css)} CSS + {len(local_js)} JS; {total} local bytes)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    for route, cfg in ROUTES.items():
        process(output, route, cfg)


if __name__ == "__main__":
    main()
