#!/usr/bin/env python3
"""Prune presentation-only legacy assets from signup/login/checkout after final commercial reducers.

The allowlists are intentionally conservative: all auth, OTP, policy, checkout,
tracking, notification and decision-guard runtimes remain. Only generic public
Radar/fallback/copy/ticker-nav and superseded conversion presentation layers are removed.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import urlsplit

ROUTES = {
    "signup": {
        "remove_css": {
            "conversion-v1.css", "public-ux.css", "site-v4.css", "buyer-readiness-v1.css",
            "conversion-v3.css", "premium-email-product-v1.css",
        },
        "remove_js": {
            "public-ux.js", "public-fallbacks-v4.js", "direct-ticker-nav-v1.js",
            "header-auth-dedupe-v6.js", "public-copy-v7.js", "conversion-state-v1.js",
            "buyer-readiness-v1.js", "auth-account-security.js", "auth-delete-security.js",
        },
        "required_css": {
            "styles.css", "email-preferences.css", "plans-v1.css", "auth.css", "auth-extra.css",
            "professional-v5.css", "mobile-touch-v1.css", "header-notifications.css", "commercial-v2.css",
        },
        "required_js": {
            "app.js", "signup-email-intent.js", "signup-link-v1.js", "auth-config.js",
            "auth-email-gate.js", "auth-policy.js", "auth.js", "auth-extra.js", "paid-nav-v1.js",
            "auth-production-gate.js", "conversion-v3.js", "decision-copy-guard-v1.js",
            "header-notifications.js", "commercial-v2.js",
        },
        "max_css": 9, "max_js": 14, "max_bytes": 275_000,
    },
    "dang-nhap": {
        "remove_css": {"conversion-v1.css", "public-ux.css", "site-v4.css", "buyer-readiness-v1.css"},
        "remove_js": {
            "public-ux.js", "public-fallbacks-v4.js", "direct-ticker-nav-v1.js",
            "header-auth-dedupe-v6.js", "public-copy-v7.js", "conversion-state-v1.js",
            "buyer-readiness-v1.js", "auth-account-security.js", "auth-delete-security.js",
        },
        "required_css": {
            "styles.css", "auth.css", "auth-extra.css", "professional-v5.css",
            "mobile-touch-v1.css", "header-notifications.css", "commercial-v2.css",
        },
        "required_js": {
            "app.js", "auth-config.js", "auth-email-gate.js", "auth-policy.js", "auth.js",
            "auth-extra.js", "paid-nav-v1.js", "auth-production-gate.js", "decision-copy-guard-v1.js",
            "header-notifications.js", "commercial-v2.js",
        },
        "max_css": 7, "max_js": 11, "max_bytes": 245_000,
    },
    "thanh-toan": {
        "remove_css": {
            "lead-v1.css", "conversion-v1.css", "public-ux.css", "site-v4.css",
            "buyer-readiness-v1.css", "conversion-v3.css",
        },
        "remove_js": {
            "auth-state-v2.js",
            "email-interest.js", "public-ux.js", "public-fallbacks-v4.js", "direct-ticker-nav-v1.js",
            "auth-production-gate.js", "header-auth-dedupe-v6.js", "public-copy-v7.js",
            "conversion-state-v1.js", "buyer-readiness-v1.js",
        },
        "required_css": {
            "styles.css", "checkout-v1.css", "professional-v5.css", "mobile-touch-v1.css",
            "header-notifications.css", "commercial-v2.css",
        },
        "required_js": {
            "auth-config.js", "app.js", "checkout-v1.js", "paid-nav-v1.js", "conversion-v3.js",
            "decision-copy-guard-v1.js", "header-notifications.js", "commercial-v2.js",
        },
        # paid-nav-v1 now owns canonical signed-in header state and session bridging;
        # keep a small explicit budget allowance for that functional runtime.
        "max_css": 6, "max_js": 8, "max_bytes": 230_000,
    },
}


def basename(ref: str) -> str:
    return Path(urlsplit(ref).path).name


def remove_asset(source: str, name: str, kind: str) -> str:
    if kind == "css":
        return re.sub(
            rf'\s*<link\b[^>]*href=["\'][^"\']*assets/{re.escape(name)}(?:\?[^"\']*)?["\'][^>]*>\s*',
            "\n", source, flags=re.I,
        )
    return re.sub(
        rf'\s*<script\b[^>]*src=["\'][^"\']*assets/{re.escape(name)}(?:\?[^"\']*)?["\'][^>]*>\s*</script>\s*',
        "\n", source, flags=re.I | re.S,
    )


def refs(source: str, kind: str) -> list[str]:
    if kind == "css":
        return re.findall(
            r'<link\b[^>]*rel=["\'][^"\']*stylesheet[^"\']*["\'][^>]*href=["\']([^"\']+)["\'][^>]*>',
            source, flags=re.I,
        )
    return re.findall(r'<script\b[^>]*src=["\']([^"\']+)["\'][^>]*>\s*</script>', source, flags=re.I | re.S)


def local_names(items: list[str]) -> set[str]:
    return {basename(ref) for ref in items if ref and not ref.startswith(("http://", "https://", "//"))}


def local_bytes(output: Path, items: list[str]) -> int:
    total = 0
    for ref in items:
        if not ref or ref.startswith(("http://", "https://", "//")):
            continue
        target = output / "assets" / basename(ref)
        if not target.is_file():
            raise RuntimeError(f"Missing local asset after conversion pruning: {ref}")
        total += target.stat().st_size
    return total


def verify_functional_markers(route: str, source: str) -> None:
    required = {
        "signup": ("data-auth-signup-form", "selected_plan", "email_daily_brief", "email_event_alerts", "data-signup-submit-label"),
        "dang-nhap": ("data-auth-login-form", "data-password-toggle"),
        "thanh-toan": ("data-checkout-qr-image", "data-checkout-reference", "data-checkout-confirm", "0934389822", "VPBank"),
    }[route]
    for marker in required:
        if marker not in source:
            raise RuntimeError(f"{route}: functional marker missing after asset pruning: {marker}")


def process(output: Path, route: str, config: dict) -> None:
    page = output / route / "index.html"
    if not page.is_file():
        raise RuntimeError(f"Missing conversion route: {page}")
    source = page.read_text(encoding="utf-8")
    for name in config["remove_css"]:
        source = remove_asset(source, name, "css")
    for name in config["remove_js"]:
        source = remove_asset(source, name, "js")
    page.write_text(source, encoding="utf-8")

    rendered = page.read_text(encoding="utf-8")
    css_refs = refs(rendered, "css")
    js_refs = refs(rendered, "js")
    css_names = local_names(css_refs)
    js_names = local_names(js_refs)

    missing_css = config["required_css"] - css_names
    missing_js = config["required_js"] - js_names
    if missing_css or missing_js:
        raise RuntimeError(f"{route}: required assets missing; css={sorted(missing_css)}, js={sorted(missing_js)}")
    survived_css = config["remove_css"] & css_names
    survived_js = config["remove_js"] & js_names
    if survived_css or survived_js:
        raise RuntimeError(f"{route}: legacy assets survived; css={sorted(survived_css)}, js={sorted(survived_js)}")
    if len(css_names) > config["max_css"] or len(js_names) > config["max_js"]:
        raise RuntimeError(f"{route}: asset count budget exceeded: {len(css_names)} CSS + {len(js_names)} JS")
    total = local_bytes(output, css_refs + js_refs)
    if total > config["max_bytes"]:
        raise RuntimeError(f"{route}: local CSS/JS budget exceeded: {total} > {config['max_bytes']}")

    verify_functional_markers(route, rendered)
    print(f"{route}: PASS ({len(css_names)} CSS + {len(js_names)} JS; {total} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_dir():
        raise RuntimeError(f"Pages output does not exist: {output}")
    for route, config in ROUTES.items():
        process(output, route, config)
    print("Conversion asset budgets: PASS (auth/billing runtimes preserved; generic public layers pruned)")


if __name__ == "__main__":
    main()
