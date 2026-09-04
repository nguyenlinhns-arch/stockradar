#!/usr/bin/env python3
"""Normalize the built plan page before the final commercial reducer.

The source plan page may evolve independently. This preflight keeps the reducer contract
stable without weakening it: one buyer-plan explainer remains for v1 to remove, and one
data-plan-comparison anchor always exists for v1 to replace.
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
    matches = list(buyer_pattern.finditer(source))
    if not matches:
        raise RuntimeError("Plan preflight expected at least one buyer-plan-value section")
    # Keep exactly the first legacy explainer because commercial v1 intentionally removes it.
    if len(matches) > 1:
        first = matches[0]
        pieces = [source[:first.end()]]
        cursor = first.end()
        for match in matches[1:]:
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
    comparison_count = len(comparison_pattern.findall(rendered))
    if buyer_count != 1:
        raise RuntimeError(f"Plan preflight expected exactly one buyer-plan-value section, found {buyer_count}")
    if comparison_count != 1:
        raise RuntimeError(f"Plan preflight expected exactly one data-plan-comparison section, found {comparison_count}")
    print("Commercial plans preflight: PASS (one removable explainer + one comparison anchor)")


if __name__ == "__main__":
    main()
