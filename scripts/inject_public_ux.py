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


def checkout_ready() -> bool:
    return os.environ.get("STOCKRADAR_CHECKOUT_READY", "").strip().lower() in {"1", "true", "yes", "on"}


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
    plans_href = route_href(source, page, output, "dang-ky")
    signup_href = route_href(source, page, output, "signup")
    signup_free_href = signup_href + "?plan=free"
    actions = (
        '<div class="header-auth-actions" data-header-auth-actions>'
        f'<a class="header-login-cta" href="{login_href}">Đăng nhập</a>'
        f'<a class="header-register-cta" href="{signup_free_href}">Đăng ký miễn phí</a>'
        f'<a href="{plans_href}" hidden aria-hidden="true" tabindex="-1">So sánh gói</a>'
        '</div>'
    )
    return source[: match.start(2)] + actions + source[match.start(2) :]


def inject_conversion_rail(source: str, page: Path, output: Path) -> str:
    route = top_route(page, output)
    if route not in CONVERSION_ROUTES or "data-conversion-rail" in source:
        return source
    if "</main>" not in source:
        return source

    plans_href = route_href(source, page, output, "dang-ky")
    signup_free_href = route_href(source, page, output, "signup") + "?plan=free"
    if checkout_ready():
        premium_href = route_href(source, page, output, "thanh-toan") + "?plan=premium"
        premium_label = "Premium · 199.000đ/30 ngày"
        premium_copy = "Premium bổ sung AI không giới hạn, lớp quyết định, Daily 09:00 và Action Alert trong phiên khi tín hiệu đủ chuẩn."
    else:
        premium_href = plans_href + "#premium"
        premium_label = "Premium · đang hoàn thiện production"
        premium_copy = "Premium đang tạm dừng kích hoạt mới cho tới khi Decision Feed và email Action Alert hoàn tất kiểm thử end-to-end."

    rail = (
        '<section class="conversion-rail" data-conversion-rail>'
        '<div class="container conversion-rail-inner">'
        '<div class="conversion-rail-copy"><span>FREE → PREMIUM</span>'
        '<strong>Bắt đầu với StockRadar AI Free 10 câu/ngày sau khi đăng nhập.</strong>'
        f'<p>Free có AI, tra cứu và watchlist cơ bản. {premium_copy}</p></div>'
        '<div class="conversion-rail-actions">'
        f'<a class="conversion-free" data-conversion-free-lead href="{signup_free_href}">Tạo tài khoản Free</a>'
        f'<a class="conversion-free" href="{plans_href}">So sánh gói</a>'
        f'<a class="conversion-premium" href="{premium_href}">{premium_label}</a>'
        '</div></div></section>'
    )
    source = source.replace("</main>", rail + "</main>", 1)

    if "conversion-mobile-cta" not in source and "</body>" in source:
        mobile = (
            '<div class="conversion-mobile-cta">'
            '<span><strong>FREE · 10 CÂU/NGÀY</strong>AI StockRadar sau khi đăng nhập</span>'
            f'<a data-conversion-mobile-lead href="{signup_free_href}">Đăng ký Free</a>'
            '</div>'
        )
        source = source.replace("</body>", mobile + "</body>", 1)
    return source


def route_specific_head(source: str, page: Path, output: Path) -> str:
    professional_css = asset_href(source, page, output, "professional-v5.css")
    conversion_css = asset_href(source, page, output, "conversion-v1.css")
    paid_nav_js = asset_href(source, page, output, "paid-nav-v1.js")
    head = (
        f'<link rel="stylesheet" href="{professional_css}?v=20260904-pro5">\n'
        f'<link rel="stylesheet" href="{conversion_css}?v=20260904-funnel2">\n'
        f'<script src="{paid_nav_js}?v=20260904-paidnav1" defer></script>\n'
    )
    if page.parent.name == "khuyen-nghi":
        css = asset_href(source, page, output, "recommendation-dense-v3.css")
        head += f'<link rel="stylesheet" href="{css}?v=20260903-reco3">\n'
    if top_route(page, output) == "tai-khoan":
        account_css = asset_href(source, page, output, "account-upgrade-v1.css")
        account_js = asset_href(source, page, output, "account-upgrade-v1.js")
        head += (
            f'<link rel="stylesheet" href="{account_css}?v=20260904-upgrade1">\n'
            f'<script src="{account_js}?v=20260904-upgrade1" defer></script>\n'
        )
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
            + f'<script src="{home_core_js}?v=20260904-homecore6" defer></script>\n'
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
        conversion_state_js = asset_href(source, page, output, "conversion-state-v1.js")
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
            + f'<script src="{conversion_state_js}?v=20260904-funnel1" defer></script>\n'
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
        output / "assets" / "conversion-state-v1.js",
        output / "assets" / "account-upgrade-v1.css",
        output / "assets" / "account-upgrade-v1.js",
        output / "assets" / "mobile-touch-v1.css",
        output / "assets" / "public-fallbacks-v4.js",
        output / "assets" / "header-auth-dedupe-v6.js",
        output / "assets" / "public-copy-v7.js",
        output / "assets" / "direct-ticker-nav-v1.js",
        output / "assets" / "home-core-v1.js",
        output / "assets" / "paid-nav-v1.js",
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
