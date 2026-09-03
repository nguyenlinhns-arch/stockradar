#!/usr/bin/env python3
"""Inject production-facing UX guards into a built StockRadar Pages artifact."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


HEAD_MARKER = "data-stockradar-public-ux"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def relative_asset(page: Path, output: Path, name: str) -> str:
    target = output / "assets" / name
    return os.path.relpath(target, page.parent).replace(os.sep, "/")


def inject_page(page: Path, output: Path) -> None:
    source = page.read_text(encoding="utf-8")
    if HEAD_MARKER in source:
        return
    if "</head>" not in source:
        raise RuntimeError(f"HTML page has no closing head tag: {page}")

    css = relative_asset(page, output, "public-ux.css")
    public_js = relative_asset(page, output, "public-ux.js")
    auth_gate_js = relative_asset(page, output, "auth-production-gate.js")
    head = (
        f'<link rel="stylesheet" href="{css}?v=20260903-public1" {HEAD_MARKER}>\n'
        f'<script src="{public_js}?v=20260903-public2" defer></script>\n'
        f'<script src="{auth_gate_js}?v=20260903-public1" defer></script>\n'
    )
    page.write_text(source.replace("</head>", head + "</head>", 1), encoding="utf-8")


def retire_public_mock_route(output: Path) -> None:
    page = output / "co-phieu" / "demo1" / "index.html"
    if not page.is_file():
        return
    page.write_text(
        """<!doctype html>
<html lang="vi">
<head>
  <base href="../../">
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <meta http-equiv="refresh" content="0;url=kiem-tra-co-phieu/">
  <title>StockRadar</title>
  <script>location.replace(new URL('kiem-tra-co-phieu/', document.baseURI).href);</script>
</head>
<body><p>Đang chuyển đến trang tra cứu StockRadar…</p></body>
</html>
""",
        encoding="utf-8",
    )


def main() -> None:
    output = parse_args().output.resolve()
    if not output.is_dir():
        raise RuntimeError(f"Pages output does not exist: {output}")

    required = [
        output / "assets" / "public-ux.css",
        output / "assets" / "public-ux.js",
        output / "assets" / "auth-production-gate.js",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"Missing production UX assets: {missing}")

    pages = sorted(output.rglob("*.html"))
    if not pages:
        raise RuntimeError("No HTML pages found in Pages artifact")
    for page in pages:
        inject_page(page, output)

    retire_public_mock_route(output)


if __name__ == "__main__":
    main()
