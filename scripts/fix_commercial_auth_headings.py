#!/usr/bin/env python3
"""Promote the compact auth card title to the page h1 after removing marketing intros."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROUTES = ("signup", "dang-nhap")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()

    for route in ROUTES:
        page = output / route / "index.html"
        if not page.is_file():
            raise RuntimeError(f"Missing auth page: {page}")
        source = page.read_text(encoding="utf-8")
        if re.search(r'<h1\b[^>]*>\s*[^<]+', source, flags=re.I):
            continue

        pattern = re.compile(
            r'(<header\b[^>]*class=["\'][^"\']*\bauth-card-header\b[^"\']*["\'][^>]*>.*?)(<h2\b([^>]*)>)(.*?)(</h2>)',
            flags=re.I | re.S,
        )
        source, count = pattern.subn(
            lambda m: f'{m.group(1)}<h1{m.group(3)}>{m.group(4)}</h1>',
            source,
            count=1,
        )
        if count != 1:
            raise RuntimeError(f"Could not promote auth heading on {route}")
        page.write_text(source, encoding="utf-8")

        rendered = page.read_text(encoding="utf-8")
        if len(re.findall(r'<h1\b', rendered, flags=re.I)) != 1:
            raise RuntimeError(f"Expected exactly one h1 on {route}")

    print("Commercial auth headings: PASS (one semantic h1 per auth page)")


if __name__ == "__main__":
    main()
