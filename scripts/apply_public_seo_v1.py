#!/usr/bin/env python3
"""Apply selective commercial SEO to the final StockRadar Pages artifact.

Stable public product routes are indexable. User-specific, billing, lead,
thin operational and dynamic stock routes remain noindex. Visible UX is untouched.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

BASE = "https://stockradar.vn"

PUBLIC_ROUTES = {
    "": ("StockRadar — AI và email điểm mua/bán", "Tra cứu cổ phiếu HOSE với AI. Premium tự động cập nhật điểm mua/bán qua email theo lượt rà soát trong phiên; xem lịch và trạng thái gửi."),
    "radar5": ("Radar HOSE — StockRadar", "Radar cổ phiếu HOSE theo trạng thái hành động. Chỉ hiển thị mã đủ điều kiện StockRadar."),
    "kiem-tra-co-phieu": ("Tra cứu cổ phiếu HOSE — StockRadar", "Nhập mã cổ phiếu HOSE để xem trạng thái và dữ liệu StockRadar."),
    "khuyen-nghi": ("Khuyến nghị cổ phiếu — StockRadar", "Danh sách tín hiệu cổ phiếu HOSE đã được StockRadar phát hành và theo dõi."),
    "nganh": ("Cổ phiếu theo ngành — StockRadar", "So sánh sức mạnh cổ phiếu theo ngành trên HOSE."),
    "hieu-qua": ("Hiệu quả StockRadar", "Lịch sử tín hiệu, kết quả và benchmark của StockRadar."),
    "dang-ky": ("Gói StockRadar — Free và Premium", "Premium: email tự động cập nhật điểm mua/bán của mã theo dõi, kèm mức giá và giờ xác nhận. Xem lịch gửi và so sánh với Free."),
}

PRIVATE_ROUTES = {
    "signup", "dang-nhap", "dat-lai-mat-khau", "tai-khoan", "thanh-toan",
    "nhan-ban-tin", "hom-nay", "co-phieu", "premium-mau", "breakout", "risk",
    "track-record", "thay-doi-hom-nay", "email", "theo-doi",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def page_path(output: Path, route: str) -> Path:
    return output / "index.html" if route == "" else output / route / "index.html"


def canonical(route: str) -> str:
    return BASE + "/" if route == "" else f"{BASE}/{route}/"


def remove_named_meta(source: str, name: str) -> str:
    return re.sub(rf'\s*<meta\b[^>]*name=["\']{re.escape(name)}["\'][^>]*>\s*', "\n", source, flags=re.I)


def remove_property_meta(source: str, prop: str) -> str:
    return re.sub(rf'\s*<meta\b[^>]*property=["\']{re.escape(prop)}["\'][^>]*>\s*', "\n", source, flags=re.I)


def set_public_meta(source: str, route: str, title: str, description: str) -> str:
    if "</head>" not in source:
        raise RuntimeError(f"SEO route missing </head>: {route or '/'}")
    url = canonical(route)
    safe_title = html.escape(title, quote=True)
    safe_desc = html.escape(description, quote=True)

    source, count = re.subn(r'<title>.*?</title>', f'<title>{safe_title}</title>', source, count=1, flags=re.I | re.S)
    if count != 1:
        raise RuntimeError(f"SEO route missing title: {route or '/'}")

    for name in ("robots", "description", "twitter:card", "twitter:title", "twitter:description"):
        source = remove_named_meta(source, name)
    for prop in ("og:site_name", "og:type", "og:title", "og:description", "og:url"):
        source = remove_property_meta(source, prop)
    source = re.sub(r'\s*<link\b[^>]*rel=["\']canonical["\'][^>]*>\s*', "\n", source, flags=re.I)

    tags = (
        '<meta name="robots" content="index,follow,max-image-preview:large">\n'
        f'<meta name="description" content="{safe_desc}">\n'
        f'<link rel="canonical" href="{url}">\n'
        '<meta property="og:site_name" content="StockRadar">\n'
        '<meta property="og:type" content="website">\n'
        f'<meta property="og:title" content="{safe_title}">\n'
        f'<meta property="og:description" content="{safe_desc}">\n'
        f'<meta property="og:url" content="{url}">\n'
        '<meta name="twitter:card" content="summary">\n'
        f'<meta name="twitter:title" content="{safe_title}">\n'
        f'<meta name="twitter:description" content="{safe_desc}">'
    )
    return source.replace("</head>", tags + "\n</head>", 1)


def ensure_noindex(source: str) -> str:
    if "</head>" not in source:
        return source
    source = remove_named_meta(source, "robots")
    return source.replace("</head>", '<meta name="robots" content="noindex,nofollow">\n</head>', 1)


def write_robots(output: Path) -> None:
    (output / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /signup/\n"
        "Disallow: /dang-nhap/\n"
        "Disallow: /dat-lai-mat-khau/\n"
        "Disallow: /tai-khoan/\n"
        "Disallow: /thanh-toan/\n"
        "Disallow: /nhan-ban-tin/\n"
        "Disallow: /co-phieu/\n"
        "Sitemap: https://stockradar.vn/sitemap.xml\n",
        encoding="utf-8",
    )


def write_sitemap(output: Path) -> None:
    body = "\n".join(f"  <url><loc>{html.escape(canonical(route))}</loc></url>" for route in PUBLIC_ROUTES)
    (output / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'{body}\n'
        '</urlset>\n',
        encoding="utf-8",
    )


def verify(output: Path) -> None:
    for route, (title, _description) in PUBLIC_ROUTES.items():
        path = page_path(output, route)
        if not path.is_file():
            raise RuntimeError(f"Missing public SEO route: {route or '/'}")
        source = path.read_text(encoding="utf-8")
        for marker in (
            'content="index,follow,max-image-preview:large"',
            f'rel="canonical" href="{canonical(route)}"',
            f'<title>{html.escape(title, quote=True)}</title>',
        ):
            if marker not in source:
                raise RuntimeError(f"Public SEO marker missing on {route or '/'}: {marker}")
        if "noindex" in source.lower():
            raise RuntimeError(f"Public route remained noindex: {route or '/'}")

    for route in PRIVATE_ROUTES:
        path = page_path(output, route)
        if path.is_file() and 'content="noindex,nofollow"' not in path.read_text(encoding="utf-8").lower():
            raise RuntimeError(f"Private/thin route became indexable: {route}")

    robots = (output / "robots.txt").read_text(encoding="utf-8")
    sitemap = (output / "sitemap.xml").read_text(encoding="utf-8")
    if "Sitemap: https://stockradar.vn/sitemap.xml" not in robots:
        raise RuntimeError("robots.txt sitemap declaration missing")
    if sitemap.count("<url>") != len(PUBLIC_ROUTES):
        raise RuntimeError("sitemap URL count mismatch")


def main() -> None:
    args = parse_args()
    output = args.output.resolve()
    for route, (title, description) in PUBLIC_ROUTES.items():
        path = page_path(output, route)
        if not path.is_file():
            raise RuntimeError(f"Missing public SEO route: {path}")
        path.write_text(set_public_meta(path.read_text(encoding="utf-8"), route, title, description), encoding="utf-8")

    for route in PRIVATE_ROUTES:
        path = page_path(output, route)
        if path.is_file():
            path.write_text(ensure_noindex(path.read_text(encoding="utf-8")), encoding="utf-8")

    write_robots(output)
    write_sitemap(output)
    verify(output)
    print(f"Public SEO: PASS ({len(PUBLIC_ROUTES)} stable indexable routes; private/thin routes noindex)")


if __name__ == "__main__":
    main()
