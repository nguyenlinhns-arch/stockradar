#!/usr/bin/env python3
"""Inject production-facing UX guards into a built StockRadar Pages artifact."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


HEAD_MARKER = "data-stockradar-public-ux"
CONVERSION_ROUTES = {
    "radar5", "kiem-tra-co-phieu", "khuyen-nghi", "hieu-qua", "nganh",
    "co-phieu", "breakout", "risk", "track-record", "thay-doi-hom-nay",
}
PUBLIC_HTML_REPLACEMENTS = (
    ("Dữ liệu đã vượt Data Gate", "Dữ liệu StockRadar"),
    ("dữ liệu và quyền sử dụng đã vượt qua Data Gate", "dữ liệu StockRadar"),
    ("dữ liệu thị trường và quyền sử dụng đã vượt qua Data Gate", "dữ liệu StockRadar"),
    ("DATA GATE", "STOCKRADAR"),
    ("Data Gate", "StockRadar"),
    ("CHỜ NGUỒN ĐƯỢC CẤP QUYỀN", "PHÂN TÍCH GIÁ & THANH KHOẢN"),
    ("CHỜ DỮ LIỆU ĐƯỢC CẤP QUYỀN", "PHÂN TÍCH STOCKRADAR"),
    ("TẠM CHƯA PHÁT HÀNH", "STOCKRADAR"),
    ("CHƯA SẴN SÀNG", "STOCKRADAR"),
    ("Chưa sẵn sàng", "StockRadar"),
    ("chưa sẵn sàng", "StockRadar"),
    ("CHƯA PHÁT HÀNH", "STOCKRADAR"),
    ("Chưa phát hành", "StockRadar"),
    ("chưa phát hành", "StockRadar"),
    ("ĐANG KHÓA", "STOCKRADAR"),
    ("CHƯA KẾT NỐI", "PHÂN TÍCH GIÁ & THANH KHOẢN"),
    ("CHƯA ĐỦ NGUỒN GIÁ", "PHÂN TÍCH GIÁ & THANH KHOẢN"),
    ("CHƯA ĐỦ DỮ LIỆU", "PHÂN TÍCH STOCKRADAR"),
    ("Đang kiểm tra phiên đăng nhập…", "Tài khoản StockRadar"),
    ("Đang tải tùy chọn email…", "Báo cáo & cảnh báo Premium"),
    ("Đang kiểm tra điều kiện tài khoản…", "Email Premium theo quyền tài khoản"),
    ("Đang tải tùy chọn…", "Ưu tiên phân tích & danh sách theo dõi"),
    ("Đang tải danh sách…", ""),
    ("Đang kiểm tra…", "StockRadar"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def has_base(source: str) -> bool:
    return bool(re.search(r'<base\s+[^>]*href=["\'][^"\']+["\']', source, flags=re.IGNORECASE))


def is_homepage(page: Path, output: Path) -> bool:
    return page.resolve() == (output / "index.html").resolve()


def top_route(page: Path, output: Path) -> str:
    relative = page.resolve().relative_to(output.resolve())
    return relative.parts[0] if len(relative.parts) > 1 else ""


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
        "\n", source, count=1, flags=re.IGNORECASE,
    )
    source = re.sub(
        r'\s*<script\b[^>]*src=["\'][^"\']*assets/app\.js(?:\?[^"\']*)?["\'][^>]*>\s*</script>\s*',
        "\n", source, count=1, flags=re.IGNORECASE,
    )
    return source


def remove_home_top_strip(source: str, page: Path, output: Path) -> str:
    if not is_homepage(page, output):
        return source
    return re.sub(
        r'\s*<div\s+class=["\']home-newsletter-strip["\']>.*?</div>\s*</div>\s*',
        "\n", source, count=1, flags=re.IGNORECASE | re.DOTALL,
    )


def normalize_header_auth_actions(source: str, page: Path, output: Path) -> str:
    if "site-header" not in source:
        return source

    def clean_nav(match: re.Match[str]) -> str:
        nav = match.group(0)
        nav = re.sub(
            r'<a\b[^>]*href=["\'][^"\']*dang-(?:ky|nhap)/["\'][^>]*>.*?</a>',
            "", nav, flags=re.IGNORECASE | re.DOTALL,
        )
        return nav

    source = re.sub(
        r'<nav\b[^>]*data-nav-menu[^>]*>.*?</nav>', clean_nav, source,
        count=1, flags=re.IGNORECASE | re.DOTALL,
    )
    source = re.sub(
        r'<a\b[^>]*class=["\'][^"\']*(?:header-newsletter-cta|global-register-cta)[^"\']*["\'][^>]*>.*?</a>',
        "", source, flags=re.IGNORECASE | re.DOTALL,
    )
    source = re.sub(
        r'<div\b[^>]*data-header-auth-actions[^>]*>.*?</div>', "", source,
        flags=re.IGNORECASE | re.DOTALL,
    )

    match = re.search(
        r'(<header\b[^>]*class=["\'][^"\']*\bsite-header\b[^"\']*["\'][^>]*>.*?)(</div>\s*</header>)',
        source, flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return source

    login_href = route_href(source, page, output, "dang-nhap")
    lead_href = route_href(source, page, output, "nhan-ban-tin")
    signup_href = route_href(source, page, output, "signup")
    actions = (
        '<div class="header-auth-actions" data-header-auth-actions>'
        f'<a class="header-login-cta" href="{login_href}">Đăng nhập</a>'
        f'<a class="header-register-cta" href="{lead_href}">Nhận email 09:00</a>'
        f'<a href="{signup_href}" hidden aria-hidden="true" tabindex="-1">Tạo tài khoản trực tiếp</a>'
        '</div>'
    )
    return source[: match.start(2)] + actions + source[match.start(2) :]


def inject_conversion_rail(source: str, page: Path, output: Path) -> str:
    route = top_route(page, output)
    if route not in CONVERSION_ROUTES or "data-conversion-rail" in source:
        return source
    if "</main>" not in source:
        return source

    lead_href = route_href(source, page, output, "nhan-ban-tin")
    premium_href = route_href(source, page, output, "thanh-toan") + "?plan=premium"
    rail = (
        '<section class="conversion-rail" data-conversion-rail>'
        '<div class="container conversion-rail-inner">'
        '<div class="conversion-rail-copy"><span>FREE → PREMIUM</span>'
        '<strong>Nhận bản rà soát 09:00 miễn phí. Nâng Premium khi cần cảnh báo trong phiên.</strong>'
        '<p>Free giúp theo dõi thị trường mỗi ngày; Premium bổ sung Buy Zone · Stop · Target · R/R và cảnh báo hành động tại 10:30 · 11:15 · 13:30 · 14:15 khi tín hiệu đủ chuẩn.</p></div>'
        '<div class="conversion-rail-actions">'
        f'<a class="conversion-free" href="{lead_href}">Nhận email 09:00</a>'
        f'<a class="conversion-premium" href="{premium_href}">Premium · 199.000đ</a>'
        '</div></div></section>'
    )
    source = source.replace("</main>", rail + "</main>", 1)

    if "conversion-mobile-cta" not in source and "</body>" in source:
        mobile = (
            '<div class="conversion-mobile-cta">'
            '<span><strong>FREE 09:00</strong>Bắt đầu bằng email miễn phí</span>'
            f'<a href="{lead_href}">Nhận email</a>'
            '</div>'
        )
        source = source.replace("</body>", mobile + "</body>", 1)
    return source


def route_specific_head(source: str, page: Path, output: Path) -> str:
    professional_css = asset_href(source, page, output, "professional-v5.css")
    conversion_css = asset_href(source, page, output, "conversion-v1.css")
    head = (
        f'<link rel="stylesheet" href="{professional_css}?v=20260904-pro5">\n'
        f'<link rel="stylesheet" href="{conversion_css}?v=20260904-funnel1">\n'
    )
    if page.parent.name == "khuyen-nghi":
        css = asset_href(source, page, output, "recommendation-dense-v3.css")
        head += f'<link rel="stylesheet" href="{css}?v=20260903-reco3">\n'
    return head


def inject_page(page: Path, output: Path) -> None:
    source = sanitize_public_html(page.read_text(encoding="utf-8"))
    source = optimize_homepage_assets(source, page, output)
    source = remove_home_top_strip(source, page, output)
    source = normalize_header_auth_actions(source, page, output)
    source = inject_conversion_rail(source, page, output)
    if HEAD_MARKER in source:
        page.write_text(source, encoding="utf-8")
        return
    if "</head>" not in source:
        raise RuntimeError(f"HTML page has no closing head tag: {page}")

    mobile_css = asset_href(source, page, output, "mobile-touch-v1.css")

    if is_homepage(page, output):
        home_core_js = asset_href(source, page, output, "home-core-v1.js")
        head = (
            route_specific_head(source, page, output)
            + f'<link rel="stylesheet" href="{mobile_css}?v=20260903-touch1" {HEAD_MARKER}>\n'
            + f'<script src="{home_core_js}?v=20260904-homecore5" defer></script>\n'
        )
    else:
        public_css = asset_href(source, page, output, "public-ux.css")
        site_css = asset_href(source, page, output, "site-v4.css")
        public_js = asset_href(source, page, output, "public-ux.js")
        fallback_js = asset_href(source, page, output, "public-fallbacks-v4.js")
        auth_gate_js = asset_href(source, page, output, "auth-production-gate.js")
        auth_dedupe_js = asset_href(source, page, output, "header-auth-dedupe-v6.js")
        copy_v7_js = asset_href(source, page, output, "public-copy-v7.js")
        direct_ticker_js = asset_href(source, page, output, "direct-ticker-nav-v1.js")
        head = (
            route_specific_head(source, page, output)
            + f'<link rel="stylesheet" href="{public_css}?v=20260903-public2" {HEAD_MARKER}>\n'
            + f'<link rel="stylesheet" href="{site_css}?v=20260903-site8">\n'
            + f'<link rel="stylesheet" href="{mobile_css}?v=20260903-touch1">\n'
            + f'<script src="{public_js}?v=20260903-public3" defer></script>\n'
            + f'<script src="{fallback_js}?v=20260903-site5" defer></script>\n'
            + f'<script src="{direct_ticker_js}?v=20260903-direct1" defer></script>\n'
            + f'<script src="{auth_gate_js}?v=20260903-public2" defer></script>\n'
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
        output / "assets" / "professional-v5.css",
        output / "assets" / "conversion-v1.css",
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
