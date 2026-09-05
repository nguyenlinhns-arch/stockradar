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
# Keep the performance gate strict. We reduce shipped bytes instead of raising this budget.
MAX_LOCAL_ASSET_BYTES = 194_000  # Includes the verified email-history summary on the homepage.
AI_CENTER_CACHE_VERSION = "20260905-email1"


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


def _colon_starts_custom_property(out: list[str]) -> bool:
    """Return True when the last emitted ':' belongs to a --custom-property name."""
    if not out or out[-1] != ":":
        return False
    idx = len(out) - 2
    while idx >= 0 and out[idx] not in "{};":
        idx -= 1
    token = "".join(out[idx + 1 : -1]).strip()
    return bool(re.fullmatch(r"--[A-Za-z0-9_-]+", token))


def _keep_pending_space(out: list[str], current: str) -> bool:
    """Keep one whitespace token only where removing it can change CSS tokenization."""
    if not out:
        return False
    previous = out[-1]
    if previous.isspace():
        return False

    # Whitespace around structural punctuation is not significant. Deliberately do not
    # strip around + / - because calc() requires whitespace around arithmetic operators.
    if current in {"{", "}", ";", ",", ")", "]", "!"}:
        return False
    if previous in {"{", "}", ";", ",", "(", "[", "!"}:
        return False

    # Normal declarations do not need the common `property: value` space. Custom
    # properties are the exception: leading whitespace is part of their token stream and
    # may be observable through var(), so preserve one whitespace token there.
    if previous == ":" and not _colon_starts_custom_property(out):
        return False
    return True


def minify_css(source: str) -> str:
    """Conservatively minify CSS without changing selectors, calc() math, or strings.

    Ordinary comments are removed exactly as CSS preprocessing removes them. Whitespace is
    collapsed to one token only when it can affect tokenization, while structural
    punctuation and normal declaration colons are compacted. Custom-property leading
    whitespace and calc() operator spacing remain intact.
    """
    out: list[str] = []
    i = 0
    quote = ""
    escaped = False
    pending_space = False
    length = len(source)

    def emit(current: str) -> None:
        nonlocal pending_space
        if pending_space and _keep_pending_space(out, current):
            out.append(" ")
        pending_space = False
        if current == "}" and out and out[-1] == ";":
            out.pop()
        out.append(current)

    while i < length:
        ch = source[i]

        if quote:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = ""
            i += 1
            continue

        if ch in {"'", '"'}:
            emit(ch)
            quote = ch
            i += 1
            continue

        if ch == "/" and i + 1 < length and source[i + 1] == "*":
            end = source.find("*/", i + 2)
            if end < 0:
                raise RuntimeError("Unterminated CSS comment during homepage minification")
            comment = source[i : end + 2]
            if comment.startswith("/*!"):
                if pending_space and _keep_pending_space(out, "/"):
                    out.append(" ")
                pending_space = False
                out.extend(comment)
            # Ordinary CSS comments disappear without inventing whitespace. Existing
            # whitespace before/after the comment is still represented by pending_space.
            i = end + 2
            continue

        if ch.isspace():
            pending_space = True
            i += 1
            continue

        emit(ch)
        i += 1

    return "".join(out).strip() + "\n"


def minify_home_css(output: Path, refs: list[str]) -> tuple[int, int]:
    """Minify only CSS actually referenced by the final homepage.

    The files live in the Pages artifact, not the repository source tree. Other pages may
    share them, so the transform must remain semantics-preserving. Return before/after
    byte totals for observability and a regression-friendly performance signal.
    """
    before = 0
    after = 0
    seen: set[str] = set()
    for ref in refs:
        if ref.startswith(("http://", "https://", "//")):
            continue
        name = basename(ref)
        if name in seen:
            continue
        seen.add(name)
        target = output / "assets" / name
        if not target.is_file():
            raise RuntimeError(f"Homepage local CSS missing before minification: {ref}")
        raw = target.read_text(encoding="utf-8")
        raw_bytes = len(raw.encode("utf-8"))
        compact = minify_css(raw)
        compact_bytes = len(compact.encode("utf-8"))
        if compact_bytes > raw_bytes:
            raise RuntimeError(f"Homepage CSS minification grew asset: {name}")
        target.write_text(compact, encoding="utf-8")
        before += raw_bytes
        after += compact_bytes
    return before, after


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

    css_before, css_after = minify_home_css(output, css_refs)
    total_bytes = local_asset_size(output, css_refs) + local_asset_size(output, js_refs)
    if total_bytes > MAX_LOCAL_ASSET_BYTES:
        raise RuntimeError(
            f"Homepage local CSS/JS budget exceeded after CSS minification: {total_bytes} > {MAX_LOCAL_ASSET_BYTES} "
            f"(CSS {css_before} -> {css_after})"
        )

    print(
        "Homepage asset budget: PASS "
        f"({local_css_count} CSS + {local_js_count} JS; {total_bytes} local bytes; "
        f"CSS {css_before}->{css_after}; exact allowlist; legacy layers pruned)"
    )


if __name__ == "__main__":
    main()
