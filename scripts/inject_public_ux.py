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
    ("CHỜ NGUỒN ĐƯỢC CẤP QUYỀN", "ĐANG CẬP NHẬT GIÁ"),
    ("CHỜ DỮ LIỆU ĐƯỢC CẤP QUYỀN", "ĐANG CẬP NHẬT DỮ LIỆU"),
    ("TẠM CHƯA PHÁT HÀNH", "ĐANG CẬP NHẬT"),
    ("CHƯA SẴN SÀNG", "ĐANG CẬP NHẬT"),
    ("Chưa sẵn sàng", "Đang cập nhật"),
    ("chưa sẵn sàng", "đang cập nhật"),
    ("CHƯA PHÁT HÀNH", "ĐANG CẬP NHẬT"),
    ("Chưa phát hành", "Đang cập nhật"),
    ("chưa phát hành", "đang cập nhật"),
    ("ĐANG KHÓA", "ĐANG CẬP NHẬT"),
    ("CHƯA KẾT NỐI", "ĐANG CẬP NHẬT"),
    ("CHƯA ĐỦ NGUỒN GIÁ", "ĐANG CẬP NHẬT GIÁ"),
    ("CHƯA ĐỦ DỮ LIỆU", "ĐANG CẬP NHẬT DỮ LIỆU"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def has_base(source: str) -> bool:
    return bool(re.search(r'<base\s+[^>]*href=["\'][^"\']+["\']', source, flags=re.IGNORECASE))


def is_homepage(page: Path, output: Path) -> bool:
    return page.resolve() == (output / "index.html").resolve()


def asset_href(source: str, page: Path, output: Path, name: str) -> str:
    if has_base(source):
        return f"assets/{name}"
    target = output / "assets" / name
    return os.path.relpath(target, page.parent).replace(os.sep, "/")


def route_href(source: str, page: Path, output: Path, route: str) -> str:
    route = route.strip("/")
    if has_base(source):
        return f"{route}/"
    target = output / route
    relative = os.path.relpath(target, page.parent).replace(os.sep, "/")
    return relative.rstrip("/") + "/"


def sanitize_public_html(source: str) -> str:
    for before, after in PUBLIC_HTML_REPLACEMENTS:
        source = source.replace(before, after)
    return source


def optimize_homepage_assets(source: str, page: Path, output: Path) -> str:
    if not is_homepage(page, output):
        return source
    source = re.sub(
        r'\s*<link\b[^>]*href=["\'][^"\']*assets/home-dashboard\.css(?:\?[^"\']*)?["\'][^>]*>\s*',
        "\n",
        source,
        count=1,
        flags=re.IGNORECASE,
    )
    source = re.sub(
        r'\s*<script\b[^>]*src=["\'][^"\']*assets/app\.js(?:\?[^"\']*)?["\'][^>]*>\s*</script>\s*',
        "\n",
        source,
        count=1,
        flags=re.IGNORECASE,
    )
    return source


def remove_home_top_strip(source: str, page: Path, output: Path) -> str:
    if not is_homepage(page, output):
        return source
    return re.sub(
        r'\s*<div\s+class=["\']home-newsletter-strip["\']>.*?</div>\s*</div>\s*',
        "\n",
        source,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )


def normalize_header_auth_actions(source: str, page: Path, output: Path) -> str:
    if "site-header" not in source:
        return source

    def clean_nav(match: re.Match[str]) -> str:
        nav = match.group(0)
        nav = re.sub(
            r'<a\b[^>]*href=["\'][^"\']*dang-(?:ky|nhap)/["\'][^>]*>.*?</a>',
            "",
            nav,
            flags=re.IGNORECASE | re.DOTALL,
        )
        return nav

    source = re.sub(
        r'<nav\b[^>]*data-nav-menu[^>]*>.*?</nav>',
        clean_nav,
        source,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )

    source = re.sub(
        r'<a\b[^>]*class=["\'][^"\']*(?:header-newsletter-cta|global-register-cta)[^"\']*["\'][^>]*>.*?</a>',
        "",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )
    source = re.sub(
        r'<div\b[^>]*data-header-auth-actions[^>]*>.*?</div>',
        "",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )

    match = re.search(
        r'(<header\b[^>]*class=["\'][^"\']*\bsite-header\b[^"\']*["\'][^>]*>.*?)(</div>\s*</header>)',
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return source

    login_href = route_href(source, page, output, "dang-nhap")
    register_href = route_href(source, page, output, "signup")
    actions = (
        '<div class="header-auth-actions" data-header-auth-actions>'
        f'<a class="header-login-cta" href="{login_href}">Đăng nhập</a>'
        f'<a class="header-register-cta" href="{register_href}">Đăng ký</a>'
        '</div>'
    )
    return source[: match.start(2)] + actions + source[match.start(2) :]


def route_specific_head(source: str, page: Path, output: Path) -> str:
    if page.parent.name == "khuyen-nghi":
        css = asset_href(source, page, output, "recommendation-dense-v3.css")
        return f'<link rel="stylesheet" href="{css}?v=20260903-reco3">\n'
    return ""


def inject_page(page: Path, output: Path) -> None:
    source = sanitize_public_html(page.read_text(encoding="utf-8"))
    source = optimize_homepage_assets(source, page, output)
    source = remove_home_top_strip(source, page, output)
    source = normalize_header_auth_actions(source, page, output)
    if HEAD_MARKER in source:
        page.write_text(source, encoding="utf-8")
        return
    if "</head>" not in source:
        raise RuntimeError(f"HTML page has no closing head tag: {page}")

    public_css = asset_href(source, page, output, "public-ux.css")
    site_css = asset_href(source, page, output, "site-v4.css")
    mobile_css = asset_href(source, page, output, "mobile-touch-v1.css")
    auth_gate_js = asset_href(source, page, output, "auth-production-gate.js")
    auth_dedupe_js = asset_href(source, page, output, "header-auth-dedupe-v6.js")
    copy_v7_js = asset_href(source, page, output, "public-copy-v7.js")

    head = (
        route_specific_head(source, page, output)
        + f'<link rel="stylesheet" href="{public_css}?v=20260903-public2" {HEAD_MARKER}>\n'
        + f'<link rel="stylesheet" href="{site_css}?v=20260903-site7">\n'
        + f'<link rel="stylesheet" href="{mobile_css}?v=20260903-touch1">\n'
    )

    if is_homepage(page, output):
        home_core_js = asset_href(source, page, output, "home-core-v1.js")
        head += f'<script src="{home_core_js}?v=20260903-homecore1" defer></script>\n'
    else:
        public_js = asset_href(source, page, output, "public-ux.js")
        fallback_js = asset_href(source, page, output, "public-fallbacks-v4.js")
        direct_ticker_js = asset_href(source, page, output, "direct-ticker-nav-v1.js")
        head += (
            f'<script src="{public_js}?v=20260903-public3" defer></script>\n'
            + f'<script src="{fallback_js}?v=20260903-site4" defer></script>\n'
            + f'<script src="{direct_ticker_js}?v=20260903-direct1" defer></script>\n'
        )

    head += (
        f'<script src="{auth_gate_js}?v=20260903-public1" defer></script>\n'
        + f'<script src="{auth_dedupe_js}?v=20260903-site6" defer></script>\n'
        + f'<script src="{copy_v7_js}?v=20260903-site7" defer></script>\n'
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
        output / "assets" / "mobile-touch-v1.css",
        output / "assets" / "public-fallbacks-v4.js",
        output / "assets" / "header-auth-dedupe-v6.js",
        output / "assets" / "public-copy-v7.js",
        output / "assets" / "direct-ticker-nav-v1.js",
        output / "assets" / "home-core-v1.js",
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