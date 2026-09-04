#!/usr/bin/env python3
"""Restore exactly one semantic h1 on compact auth pages after marketing intros are removed."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROUTE_TITLES = {
    "signup": "Tạo tài khoản",
    "dang-nhap": "Đăng nhập",
}


def promote_known_title(source: str, title: str) -> tuple[str, int]:
    """Promote the known auth-card title without depending on its wrapper tag/class."""
    title_pattern = re.escape(title)
    pattern = re.compile(
        rf'<h2\b([^>]*)>\s*{title_pattern}\s*</h2>',
        flags=re.I | re.S,
    )
    return pattern.subn(lambda m: f'<h1{m.group(1)}>{title}</h1>', source, count=1)


def promote_first_auth_card_h2(source: str) -> tuple[str, int]:
    """Fallback: promote the first h2 inside the auth card, regardless of wrapper markup."""
    card_match = re.search(
        r'<(?:section|article|div)\b[^>]*class=["\'][^"\']*\bauth-card\b[^"\']*["\'][^>]*>(.*?)</(?:section|article|div)>',
        source,
        flags=re.I | re.S,
    )
    if not card_match:
        return source, 0

    card_html = card_match.group(0)
    promoted, count = re.subn(
        r'<h2\b([^>]*)>(.*?)</h2>',
        lambda m: f'<h1{m.group(1)}>{m.group(2)}</h1>',
        card_html,
        count=1,
        flags=re.I | re.S,
    )
    if count != 1:
        return source, 0
    start, end = card_match.span()
    return source[:start] + promoted + source[end:], 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()

    for route, title in ROUTE_TITLES.items():
        page = output / route / "index.html"
        if not page.is_file():
            raise RuntimeError(f"Missing auth page: {page}")

        source = page.read_text(encoding="utf-8")
        existing_h1 = len(re.findall(r'<h1\b', source, flags=re.I))
        if existing_h1 > 1:
            raise RuntimeError(f"Expected at most one h1 before promotion on {route}, found {existing_h1}")

        if existing_h1 == 0:
            source, count = promote_known_title(source, title)
            if count != 1:
                source, count = promote_first_auth_card_h2(source)
            if count != 1:
                raise RuntimeError(f"Could not promote auth heading on {route}")
            page.write_text(source, encoding="utf-8")

        rendered = page.read_text(encoding="utf-8")
        h1_tags = re.findall(r'<h1\b[^>]*>(.*?)</h1>', rendered, flags=re.I | re.S)
        if len(h1_tags) != 1:
            raise RuntimeError(f"Expected exactly one h1 on {route}, found {len(h1_tags)}")
        visible = re.sub(r'<[^>]+>', '', h1_tags[0]).strip()
        if visible.lower() != title.lower():
            raise RuntimeError(f"Unexpected h1 on {route}: {visible!r}")

    print("Commercial auth headings: PASS (one semantic h1 per auth page)")


if __name__ == "__main__":
    main()
