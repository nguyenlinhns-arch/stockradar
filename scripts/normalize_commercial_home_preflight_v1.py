#!/usr/bin/env python3
"""Remove redundant homepage lead form before the final commercial reducer.

StockRadar AI is the primary homepage action. Premium email preference belongs in the
plan/signup/account flow, so the old mini email form must not compete with the AI CTA.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    page = args.output.resolve() / "index.html"
    if not page.is_file():
        raise RuntimeError(f"Homepage missing: {page}")

    source = page.read_text(encoding="utf-8")
    pattern = re.compile(
        r'\s*<form\b(?=[^>]*\bdata-home-email-form\b)(?=[^>]*class=["\'][^"\']*\bhome-email-form\b[^"\']*["\'])[^>]*>.*?</form>\s*',
        flags=re.I | re.S,
    )
    source, count = pattern.subn("\n", source, count=1)
    if count != 1:
        raise RuntimeError(f"Expected exactly one homepage mini email form, removed {count}")

    page.write_text(source, encoding="utf-8")
    rendered = page.read_text(encoding="utf-8")
    for marker in ("data-home-email-form", "email-mini home-email-form"):
        if marker in rendered:
            raise RuntimeError(f"Homepage mini email marker survived: {marker}")
    if "data-stockradar-ai-center" not in rendered:
        raise RuntimeError("StockRadar AI center missing after homepage preflight")
    print("Commercial homepage preflight: PASS (redundant mini email form removed; AI preserved)")


if __name__ == "__main__":
    main()
