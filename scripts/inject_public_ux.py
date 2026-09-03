#!/usr/bin/env python3
"""Inject production-facing UX guards into a built StockRadar Pages artifact."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


HEAD_MARKER = "data-stockradar-public-ux"
PUBLIC_HTML_REPLACEMENTS = (
    ("Dữ liệu đã vượt Data Gate", "Dữ liệu đã đạt điều kiện phát hành"),
    ("dữ liệu và quyền sử dụng đã vượt qua Data Gate", "dữ liệu và quyền sử dụng đã đạt điều kiện phát hành"),
    ("dữ liệu thị trường và quyền sử dụng đã vượt qua Data Gate", "dữ liệu thị trường và quyền sử dụng đã đạt điều kiện phát hành"),
    ("DATA GATE", "TRẠNG THÁI DỮ LIỆU"),
    ("Data Gate", "điều kiện phát hành dữ liệu"),
    ("CHỜ NGUỒN ĐƯỢC CẤP QUYỀN", "TẠM CHƯA PHÁT HÀNH"),
    ("CHỜ DỮ LIỆU ĐƯỢC CẤP QUYỀN", "CHƯA ĐỦ DỮ LIỆU"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def asset_href(source: str, page: Path, output: Path, name: str) -> str:
    # Most StockRadar route pages set <base href="../"> (or another route-root
    # base). In that case asset URLs must be relative to the HTML base, not the
    # file-system depth of the generated page. Without a base element, fall back
    # to the actual relative file-system path.
    if re.search(r'<base\s+[^>]*href=["\'][^"\']+["\']', source, flags=re.IGNORECASE):
        return f"assets/{name}"
    target = output / "assets" / name
    return os.path.relpath(target, page.parent).replace(os.sep, "/")


def sanitize_public_html(source: str) -> str:
    for before, after in PUBLIC_HTML_REPLACEMENTS:
        source = source.replace(before, after)
    return source


def inject_page(page: Path, output: Path) -> None:
    source = sanitize_public_html(page.read_text(encoding="utf-8"))
    if HEAD_MARKER in source:
        page.write_text(source, encoding="utf-8")
        return
    if "</head>" not in source:
        raise RuntimeError(f"HTML page has no closing head tag: {page}")

    css = asset_href(source, page, output, "public-ux.css")
    public_js = asset_href(source, page, output, "public-ux.js")
    auth_gate_js = asset_href(source, page, output, "auth-production-gate.js")
    head = (
        f'<link rel="stylesheet" href="{css}?v=20260903-public1" {HEAD_MARKER}>\n'
        f'<script src="{public_js}?v=20260903-public3" defer></script>\n'
        f'<script src="{auth_gate_js}?v=20260903-public1" defer></script>\n'
    )
    page.write_text(source.replace("</head>", head + "</head>", 1), encoding="utf-8")


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


if __name__ == "__main__":
    main()
