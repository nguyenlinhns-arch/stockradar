#!/usr/bin/env python3
"""Prune legacy homepage assets after all commercial reducers and enforce a hard local asset budget."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import urlsplit

REMOVE_CSS = {
    "home-focus-v1.css",
    "home-conversion-v2.css",
    "conversion-v1.css",
    "home-radar-polish-v1.css",
    "buyer-readiness-v1.css",
    "conversion-v3.css",
    "premium-email-product-v1.css",
    "ai-assistant.css",
}
REMOVE_JS = {
    "buyer-readiness-v1.js",
    "conversion-v3.js",
    "ai-assistant.js",
}
REQUIRED_CSS = {
    "styles.css",
    "home-ai-center-v1.css",
    "home-workspace-v2.css",
    "professional-v5.css",
    "mobile-touch-v1.css",
    "commercial-v1.css",
    "header-notifications.css",
}
REQUIRED_JS = {
    "auth-config.js",
    "auth-state-v2.js",
    "ai-center.js",
    "home-workspace-v2.js",
    "paid-nav-v1.js",
    "home-core-v1.js",
    "decision-copy-guard-v1.js",
    "commercial-v1.js",
    "header-notifications.js",
}
MAX_LOCAL_ASSET_BYTES = 190_000
AI_CENTER_CACHE_VERSION = "20260905-ai5"


def basename(ref: str) -> str:
    return Path(urlsplit(ref).path).name


def extract_css(source: str) -> list[str]:
    return re.findall(
        r'<link\b[^>]*rel=["\'][^"\']*stylesheet[^"\']*["\'][^>]*href=["\']([^"\']+)["\'][^>]*>',
        source,
        flags=re.I,
    )


def extract_js(source: str) -> list[str]:
    return re.findall(r'<script\b[^>]*src=["\']([^"\']+)["\'][^>]*>\s*</script>', source, flags=re.I | re.S)


def local_asset_size(output: Path, refs: list[str]) -> int:
    total = 0
    for ref in refs:
        if ref.startswith(("http://", "https://", "//")):
            continue
        name = basename(ref)
        target = output / "assets" / name
        if not target.is_file():
            raise RuntimeError(f"Homepage local asset missing: {ref}")
        total += target.stat().st_size
    return total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    page = output / "index.html"
    if not page.is_file():
        raise RuntimeError("Homepage missing from Pages artifact")

    source = page.read_text(encoding="utf-8")
    source, ai_count = re.subn(
        r'assets/ai-center\.js(?:\?[^"\']*)?',
        f'assets/ai-center.js?v={AI_CENTER_CACHE_VERSION}',
        source,
        count=1,
        flags=re.I,
    )
    if ai_count != 1:
        raise RuntimeError("Homepage ai-center.js reference missing before cache normalization")

    for name in REMOVE_CSS:
        source = re.sub(
            rf'\s*<link\b[^>]*href=["\'][^"\']*assets/{re.escape(name)}(?:\?[^"\']*)?["\'][^>]*>\s*',
            "\n",
            source,
            flags=re.I,
        )
    for name in REMOVE_JS:
        source = re.sub(
            rf'\s*<script\b[^>]*src=["\'][^"\']*assets/{re.escape(name)}(?:\?[^"\']*)?["\'][^>]*>\s*</script>\s*',
            "\n",
            source,
            flags=re.I | re.S,
        )

    page.write_text(source, encoding="utf-8")
    rendered = page.read_text(encoding="utf-8")
    if f"assets/ai-center.js?v={AI_CENTER_CACHE_VERSION}" not in rendered:
        raise RuntimeError("Homepage ai-center.js cache version was not normalized")
    css_refs = extract_css(rendered)
    js_refs = extract_js(rendered)
    css_names = {basename(ref) for ref in css_refs if not ref.startswith(("http://", "https://", "//"))}
    js_names = {basename(ref) for ref in js_refs if not ref.startswith(("http://", "https://", "//"))}

    missing_css = REQUIRED_CSS - css_names
    missing_js = REQUIRED_JS - js_names
    if missing_css:
        raise RuntimeError(f"Homepage essential CSS missing after pruning: {sorted(missing_css)}")
    if missing_js:
        raise RuntimeError(f"Homepage essential JS missing after pruning: {sorted(missing_js)}")

    survived_css = REMOVE_CSS & css_names
    survived_js = REMOVE_JS & js_names
    if survived_css or survived_js:
        raise RuntimeError(f"Legacy homepage assets survived: css={sorted(survived_css)}, js={sorted(survived_js)}")

    # Exact allowlists: a new homepage asset must be deliberately reviewed before it can ship.
    extra_css = css_names - REQUIRED_CSS
    extra_js = js_names - REQUIRED_JS
    if extra_css:
        raise RuntimeError(f"Unreviewed homepage CSS detected: {sorted(extra_css)}")
    if extra_js:
        raise RuntimeError(f"Unreviewed homepage JS detected: {sorted(extra_js)}")

    local_css_count = len(css_names)
    local_js_count = len(js_names)
    if local_css_count != len(REQUIRED_CSS):
        raise RuntimeError(f"Homepage CSS allowlist mismatch: {local_css_count} != {len(REQUIRED_CSS)}")
    if local_js_count != len(REQUIRED_JS):
        raise RuntimeError(f"Homepage JS allowlist mismatch: {local_js_count} != {len(REQUIRED_JS)}")

    total_bytes = local_asset_size(output, css_refs) + local_asset_size(output, js_refs)
    if total_bytes > MAX_LOCAL_ASSET_BYTES:
        raise RuntimeError(f"Homepage local CSS/JS budget exceeded: {total_bytes} > {MAX_LOCAL_ASSET_BYTES}")

    print(
        "Homepage asset budget: PASS "
        f"({local_css_count} CSS + {local_js_count} JS; {total_bytes} local bytes; exact allowlist; legacy layers pruned)"
    )


if __name__ == "__main__":
    main()
