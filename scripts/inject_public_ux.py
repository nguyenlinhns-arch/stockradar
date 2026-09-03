#!/usr/bin/env python3
"""Inject production-facing UX guards into a built StockRadar Pages artifact."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


HEAD_MARKER = "data-stockradar-public-ux"
REGISTER_MARKER = "data-global-register-cta"
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


def has_base(source: str) -> bool:
    return bool(re.search(r'<base\s+[^>]*href=["\'][^"\']+["\']', source, flags=re.IGNORECASE))


def asset_href(source: str, page: Path, output: Path, name: str) -> str:
    if has_base(source):
        return f"assets/{name}"
    target = output / "assets" / name
    return os.path.relpath(target, page.parent).replace(os.sep, "/")


def registration_href(source: str, page: Path, output: Path) -> str:
    if has_base(source):
        return "dang-ky/"
    target = output / "dang-ky"
    relative = os.path.relpath(target, page.parent).replace(os.sep, "/")
    return relative.rstrip("/") + "/"


def sanitize_public_html(source: str) -> str:
    for before, after in PUBLIC_HTML_REPLACEMENTS:
        source = source.replace(before, after)
    return source


def remove_home_top_strip(source: str, page: Path, output: Path) -> str:
    """Keep the homepage header compact by removing the old top newsletter ribbon.

    Registration remains available in the main header, homepage conversion modules,
    mobile CTA and the dedicated /dang-ky/ page.
    """
    if page.resolve() != (output / "index.html").resolve():
        return source
    return re.sub(
        r'\s*<div\s+class=["\']home-newsletter-strip["\']>.*?</div>\s*</div>\s*',
        "\n",
        source,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )


def inject_registration_cta(source: str, page: Path, output: Path) -> str:
    if REGISTER_MARKER in source or "header-newsletter-cta" in source:
        return source
    if "site-header" not in source:
        return source

    match = re.search(
        r'(<header\b[^>]*class=["\'][^"\']*\bsite-header\b[^"\']*["\'][^>]*>.*?)(</div>\s*</header>)',
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return source

    href = registration_href(source, page, output)
    cta = f'<a class="global-register-cta" {REGISTER_MARKER} href="{href}">Đăng ký</a>'
    return source[: match.start(2)] + cta + source[match.start(2) :]


def route_specific_head(source: str, page: Path, output: Path) -> str:
    if page.parent.name == "khuyen-nghi":
        css = asset_href(source, page, output, "recommendation-dense-v3.css")
        return f'<link rel="stylesheet" href="{css}?v=20260903-reco3">\n'
    return ""


def inject_page(page: Path, output: Path) -> None:
    source = sanitize_public_html(page.read_text(encoding="utf-8"))
    source = remove_home_top_strip(source, page, output)
    source = inject_registration_cta(source, page, output)
    if HEAD_MARKER in source:
        page.write_text(source, encoding="utf-8")
        return
    if "</head>" not in source:
        raise RuntimeError(f"HTML page has no closing head tag: {page}")

    public_css = asset_href(source, page, output, "public-ux.css")
    site_css = asset_href(source, page, output, "site-v4.css")
    public_js = asset_href(source, page, output, "public-ux.js")
    auth_gate_js = asset_href(source, page, output, "auth-production-gate.js")
    fallback_js = asset_href(source, page, output, "public-fallbacks-v4.js")
    head = (
        route_specific_head(source, page, output)
        + f'<link rel="stylesheet" href="{public_css}?v=20260903-public2" {HEAD_MARKER}>\n'
        + f'<link rel="stylesheet" href="{site_css}?v=20260903-site4">\n'
        + f'<script src="{public_js}?v=20260903-public3" defer></script>\n'
        + f'<script src="{auth_gate_js}?v=20260903-public1" defer></script>\n'
        + f'<script src="{fallback_js}?v=20260903-site4" defer></script>\n'
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
        output / "assets" / "recommendation-dense-v3.css",
        output / "assets" / "site-v4.css",
        output / "assets" / "public-fallbacks-v4.js",
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
