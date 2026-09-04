#!/usr/bin/env python3
"""Apply selective commercial SEO to the final StockRadar Pages artifact.

Only stable public product routes are indexable. Auth, billing, personal dashboard,
lead capture, dynamic generic stock lookup and thin operational routes stay noindex.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

BASE = "https://stockradar.vn"

PUBLIC_ROUTES = {
    "": (
        "StockRadar — AI hỗ trợ quyết định cổ phiếu HOSE",
        "StockRadar giúp tra cứu, sàng lọc và theo dõi cổ phiếu HOSE bằng AI, Radar, khuyến nghị, hiệu quả và quản trị rủi ro.",
    ),
    "radar5": (
        "Radar HOSE — StockRadar",
        "Radar StockRadar sàng lọc cổ phiếu HOSE theo trạng thái, sức mạnh và mức độ đáng chú ý để người dùng theo dõi nhanh.",
    ),
    "kiem-tra-co-phieu": (
        "Tra cứu cổ phiếu HOSE — StockRadar",
        "Tra cứu nhanh cổ phiếu HOSE trên StockRadar và chuyển sang StockRadar AI để nhận câu trả lời theo từng mã.",
    ),
    "khuyen-nghi": (
        "Khuyến nghị cổ phiếu — StockRadar",
        "Danh sách tín hiệu và khuyến nghị StockRadar đã phát hành trên HOSE, kèm trạng thái để người dùng theo dõi và kiểm chứng.",
    ),
    "nganh": (
        "Cổ phiếu theo ngành — StockRadar",
        "So sánh cổ phiếu HOSE theo ngành trên StockRadar để nhận biết nhóm và mã đang nổi bật.",
    ),
    "hieu-qua": (
        "Hiệu quả khuyến nghị — StockRadar",
        "Theo dõi lịch sử tín hiệu, P/L và benchmark của StockRadar để kiểm chứng hiệu quả trước khi sử dụng Premium.",
    ),
    "dang-ky": (
        "Gói Free và Premium — StockRadar",
        "So sánh StockRadar Free và Premium: AI, Radar, My StockRadar, lớp quyết định và quyền cảnh báo theo gói.",
    ),
}

PRIVATE_ROUTES = {
    "signup", "dang-nhap", "dat-lai-mat-khau", "tai-khoan", "thanh-toan",
    "nhan-ban-tin", "hom-nay", "co-phieu", "premium-mau", "404.html",
    "breakout", "risk", "track-record", "thay-doi-hom-nay", "dieu-khoan", "quyen-rieng-tu",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def page_path(output: Path, route: str) -> Path:
    return output / "index.html" if route == "" else output / route / "index.html"


def canonical(route: str) -> str:
    return BASE + "/" if route == "" else f"{BASE}/{route}/"


def set_meta(source: str, route: str, title: str, description: str) -> str:
    url = canonical(route)
    safe_title = html.escape(title, quote=True)
    safe_desc = html.escape(description, quote=True)
    safe_url = html.escape(url, quote=True)

    source = re.sub(r'<meta\s+name=["\']robots["\']\s+content=["\'][^"\']*["\']\s*/?>',
                    '<meta name="robots" content="index,follow,max-image-preview:large">',
                    source, count=1, flags=re.I)
    if 'name="robots"' not in source.lower():
        source = source.replace("<head>", '<head><meta name="robots" content="index,follow,max-image-preview:large">', 1)

    source = re.sub(r'<title>.*?</title>', f'<title>{safe_title}</title>', source, count=1, flags=re.I | re.S)
    if re.search(r'<meta\s+name=["\']description["\']', source, flags=re.I):
        source = re.sub(r'<meta\s+name=["\']description["\']\s+content=["\'][^"\']*["\']\s*/?>',
                        f'<meta name="description" content="{safe_desc}">', source, count=1, flags=re.I)
    else:
        source = source.replace("</title>", f'</title><meta name="description" content="{safe_desc}">', 1)

    source = re.sub(r'\s*<link\s+rel=["\']canonical["\']\s+href=["\'][^"\']*["\']\s*/?>', "", source, flags=re.I)
    source = source.replace("</head>", f'<link rel="canonical" href="{safe_url}">\n</head>', 1)

    # Replace or append a compact social metadata set.
    for pattern in (
        r'\s*<meta\s+property=["\']og:(?:site_name|type|title|description|url)["\'][^>]*>',
        r'\s*<meta\s+name=["\']twitter:(?:card|title|description)["\'][^>]*>',
    ):
        source = re.sub(pattern, "", source, flags=re.I)
    social = (
        '<meta property="og:site_name" content="StockRadar">\n'
        '<meta property="og:type" content="website">\n'
        f'<meta property="og:title" content="{safe_title}">\n'
        f'<meta property="og:description" content="{safe_desc}">\n'
        f'<meta property="og:url" content="{safe_url}">\n'
        '<meta name="twitter:card" content="summary">\n'
        f'<meta name="twitter:title" content="{safe_title}">\n'
        f'<meta name="twitter:description" content="{safe_desc}">\n'
    )
    source = source.replace("</head>", social + "</head>", 1)
    return source


def ensure_noindex(source: str) -> str:
    source = re.sub(r'<meta\s+name=["\']robots["\']\s+content=["\'][^"\']*["\']\s*/?>',
                    '<meta name="robots" content="noindex,nofollow">', source, count=1, flags=re.I)
    if 'name="robots"' not in source.lower():
        source = source.replace("<head>", '<head><meta name="robots" content="noindex,nofollow">', 1)
    return source


def index_static_ticker_pages(output: Path) -> list[str]:
    urls: list[str] = []
    stock_root = output / "co-phieu"
    if not stock_root.is_dir():
        return urls
    for page in sorted(stock_root.glob("*/index.html")):
        source = page.read_text(encoding="utf-8")
        match = re.search(r'data-static-ticker=["\']([A-Z0-9]{3})["\']', source)
        if not match:
            continue
        ticker = match.group(1)
        url = f"{BASE}/co-phieu/{ticker}/"
        source = re.sub(r'<meta\s+name=["\']robots["\']\s+content=["\'][^"\']*["\']\s*/?>',
                        '<meta name="robots" content="index,follow,max-image-preview:large">', source, count=1, flags=re.I)
        if 'name="robots"' not in source.lower():
            source = source.replace("<head>", '<head><meta name="robots" content="index,follow,max-image-preview:large">', 1)
        if not re.search(r'<link\s+rel=["\']canonical["\']', source, flags=re.I):
            source = source.replace("</head>", f'<link rel="canonical" href="{url}">\n</head>', 1)
        page.write_text(source, encoding="utf-8")
        urls.append(url)
    return urls


def write_robots(output: Path) -> None:
    text = """User-agent: *
Allow: /
Disallow: /signup/
Disallow: /dang-nhap/
Disallow: /dat-lai-mat-khau/
Disallow: /tai-khoan/
Disallow: /thanh-toan/
Disallow: /nhan-ban-tin/
Disallow: /premium-mau/

Sitemap: https://stockradar.vn/sitemap.xml
"""
    (output / "robots.txt").write_text(text, encoding="utf-8")


def write_sitemap(output: Path, ticker_urls: list[str]) -> None:
    urls = [canonical(route) for route in PUBLIC_ROUTES] + ticker_urls
    body = "\n".join(f"  <url><loc>{html.escape(url)}</loc></url>" for url in urls)
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n'
    (output / "sitemap.xml").write_text(xml, encoding="utf-8")


def verify(output: Path, ticker_urls: list[str]) -> None:
    for route in PUBLIC_ROUTES:
        path = page_path(output, route)
        source = path.read_text(encoding="utf-8")
        if 'content="index,follow,max-image-preview:large"' not in source:
            raise RuntimeError(f"Public SEO route is not indexable: {route or '/'}")
        if canonical(route) not in source:
            raise RuntimeError(f"Canonical missing: {route or '/'}")
    for route in PRIVATE_ROUTES:
        path = output / route / "index.html" if route != "404.html" else output / "404.html"
        if not path.is_file():
            continue
        if 'content="noindex,nofollow"' not in path.read_text(encoding="utf-8"):
            raise RuntimeError(f"Private/thin route became indexable: {route}")
    robots = (output / "robots.txt").read_text(encoding="utf-8")
    sitemap = (output / "sitemap.xml").read_text(encoding="utf-8")
    if "Sitemap: https://stockradar.vn/sitemap.xml" not in robots:
        raise RuntimeError("robots.txt sitemap declaration missing")
    for url in [canonical(route) for route in PUBLIC_ROUTES] + ticker_urls:
        if url not in sitemap:
            raise RuntimeError(f"Sitemap URL missing: {url}")
    print(f"Public SEO: PASS ({len(PUBLIC_ROUTES)} core routes + {len(ticker_urls)} static ticker routes)")


def main() -> None:
    args = parse_args()
    output = args.output.resolve()
    for route, (title, description) in PUBLIC_ROUTES.items():
        path = page_path(output, route)
        if not path.is_file():
            raise RuntimeError(f"Missing public SEO route: {path}")
        path.write_text(set_meta(path.read_text(encoding="utf-8"), route, title, description), encoding="utf-8")

    # Reassert noindex on user-specific and thin operational routes.
    for route in PRIVATE_ROUTES:
        path = output / route / "index.html" if route != "404.html" else output / "404.html"
        if path.is_file():
            path.write_text(ensure_noindex(path.read_text(encoding="utf-8")), encoding="utf-8")

    ticker_urls = index_static_ticker_pages(output)
    write_robots(output)
    write_sitemap(output, ticker_urls)
    verify(output, ticker_urls)


if __name__ == "__main__":
    main()
