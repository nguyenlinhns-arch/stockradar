#!/usr/bin/env python3
"""Normalize commercial pricing copy in the built Pages artifact before final reducers."""

from __future__ import annotations

import argparse
from pathlib import Path

REPLACEMENTS = (
    ("199K/tháng", "199K/30 ngày"),
    ("199K / tháng", "199K / 30 ngày"),
    ("199.000đ/tháng", "199.000đ/30 ngày"),
    ("199.000đ / tháng", "199.000đ / 30 ngày"),
    ("199.000đ mỗi tháng", "199.000đ / 30 ngày"),
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    page = output / "dang-ky" / "index.html"
    if not page.is_file():
        raise RuntimeError(f"Missing pricing page: {page}")
    source = page.read_text(encoding="utf-8")
    for old, new in REPLACEMENTS:
        source = source.replace(old, new)
    page.write_text(source, encoding="utf-8")
    for old, _ in REPLACEMENTS:
        if old in source:
            raise RuntimeError(f"Stale commercial pricing survived normalization: {old}")
    print("Commercial pricing normalization: PASS (199K/30 ngày)")


if __name__ == "__main__":
    main()
