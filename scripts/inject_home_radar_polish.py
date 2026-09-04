#!/usr/bin/env python3
"""Inject the homepage Radar polish stylesheet into a built Pages artifact."""

from __future__ import annotations

import argparse
from pathlib import Path


MARKER = "home-radar-polish-v1.css"
LINK = '<link rel="stylesheet" href="assets/home-radar-polish-v1.css?v=20260904-radar1">\n'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    home = args.output.resolve() / "index.html"
    if not home.is_file():
        raise RuntimeError(f"Homepage not found: {home}")

    source = home.read_text(encoding="utf-8")
    if MARKER in source:
        return
    if "</head>" not in source:
        raise RuntimeError("Homepage has no closing head tag")

    home.write_text(source.replace("</head>", LINK + "</head>", 1), encoding="utf-8")


if __name__ == "__main__":
    main()
