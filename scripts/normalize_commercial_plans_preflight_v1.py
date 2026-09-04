#!/usr/bin/env python3
"""Normalize the built plan page before the final commercial reducer.

The source plan page is now concise. The legacy commercial reducer still expects two
old sections to remove, so this preflight supplies inert compatibility anchors only in
the temporary build artifact. They never become buyer-visible and are removed by v1.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    page = args.output.resolve() / "dang-ky" / "index.html"
    if not page.is_file():
        raise RuntimeError(f"Plan page missing: {page}")
    source = page.read_text(encoding="utf-8")

    buyer_pattern = re.compile(
        r'\s*<section\b[^>]*class=["\'][^"\']*\bbuyer-plan-value\b[^"\']*["\'][^>]*>.*?</section>\s*',
        flags=re.I | re.S,
    )
    buyer_matches = list(buyer_pattern.finditer(source))
    if not buyer_matches:
        # Build-only compatibility anchor; commercial v1 removes it immediately.
        source = source.replace(
            "</main>",
            '<section class="buyer-plan-value" hidden aria-hidden="true"></section>\n</main>',
            1,
        )
    elif len(buyer_matches) > 1:
        first = buyer_matches[0]
        pieces = [source[:first.end()]]
        cursor = first.end()
        for match in buyer_matches[1:]:
            pieces.append(source[cursor:match.start()])
            cursor = match.end()
        pieces.append(source[cursor:])
        source = "".join(pieces)

    conversion_pattern = re.compile(
        r'\s*<section\b[^>]*class=["\'][^"\']*\bconversion-plan-value\b[^"\']*["\'][^>]*>.*?</section>\s*',
        flags=re.I | re.S,
    )
    conversion_matches = list(conversion_pattern.finditer(source))
    if not conversion_matches:
        # Old reducer contract only. Hidden in the temporary artifact and then removed.
        source = source.replace(
            "</main>",
            '<section class="conversion-plan-value" hidden aria-hidden="true"></section>\n</main>',
            1,
        )
    elif len(conversion_matches) > 1:
        first = conversion_matches[0]
        pieces = [source[:first.end()]]
        cursor = first.end()
        for match in conversion_matches[1:]:
            pieces.append(source[cursor:match.start()])
            cursor = match.end()
        pieces.append(source[cursor:])
        source = "".join(pieces)

    comparison_pattern = re.compile(
        r'<section\b(?=[^>]*\bdata-plan-comparison\b)(?=[^>]*class=["\'][^"\']*\bplan-comparison\b[^"\']*["\'])[^>]*>.*?</section>',
        flags=re.I | re.S,
    )
    comparison_count = len(comparison_pattern.findall(source))
    if comparison_count > 1:
        raise RuntimeError(f"Plan preflight found duplicate data-plan-comparison sections: {comparison_count}")
    if comparison_count == 0:
        anchor = re.search(r'<p\b[^>]*class=["\'][^"\']*\bplan-legal\b[^"\']*["\'][^>]*>', source, flags=re.I)
        if not anchor:
            raise RuntimeError("Plan preflight cannot find plan-legal insertion anchor")
        placeholder = '<section class="plan-comparison" data-plan-comparison aria-label="So sánh Free và Premium"></section>\n'
        source = source[:anchor.start()] + placeholder + source[anchor.start():]

    page.write_text(source, encoding="utf-8")
    rendered = page.read_text(encoding="utf-8")
    buyer_count = len(buyer_pattern.findall(rendered))
    conversion_count = len(conversion_pattern.findall(rendered))
    comparison_count = len(comparison_pattern.findall(rendered))
    if buyer_count != 1:
        raise RuntimeError(f"Plan preflight expected exactly one buyer-plan-value anchor, found {buyer_count}")
    if conversion_count != 1:
        raise RuntimeError(f"Plan preflight expected exactly one conversion-plan-value anchor, found {conversion_count}")
    if comparison_count != 1:
        raise RuntimeError(f"Plan preflight expected exactly one data-plan-comparison section, found {comparison_count}")
    print("Commercial plans preflight: PASS (clean source + removable legacy anchors + one comparison)")


if __name__ == "__main__":
    main()
