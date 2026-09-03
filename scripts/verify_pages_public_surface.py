#!/usr/bin/env python3
"""Verify the generated GitHub Pages artifact is production-facing and self-contained."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit


FORBIDDEN_PUBLIC_TERMS = (
    "DEMO", "MOCK", "MÔ PHỎNG", "FIXTURE", "SHADOW",
    "MẪU BÁO CÁO", "MẪU EMAIL", "DỮ LIỆU MẪU", "MINH HỌA", "MINH HOẠ",
)
FORBIDDEN_HTML_TERMS = (
    "DATA GATE", "CHƯA SẴN SÀNG", "CHƯA PHÁT HÀNH",
    "CHƯA CÓ SETUP", "ĐANG HOÀN THIỆN", "TRẠNG THÁI CÔNG KHAI",
)
HOME_UX_ASSETS = (
    "assets/mobile-touch-v1.css",
    "assets/home-core-v1.js",
)
NON_HOME_UX_ASSETS = (
    "assets/public-ux.css",
    "assets/site-v4.css",
    "assets/mobile-touch-v1.css",
    "assets/public-ux.js",
    "assets/public-fallbacks-v4.js",
    "assets/direct-ticker-nav-v1.js",
    "assets/auth-production-gate.js",
    "assets/header-auth-dedupe-v6.js",
    "assets/public-copy-v7.js",
)
HOMEPAGE_FORBIDDEN_ASSETS = (
    "assets/app.js",
    "assets/home-dashboard.css",
    "assets/site-v4.css",
    "assets/public-ux.css",
    "assets/public-ux.js",
    "assets/public-fallbacks-v4.js",
    "assets/direct-ticker-nav-v1.js",
    "assets/auth-production-gate.js",
    "assets/header-auth-dedupe-v6.js",
    "assets/public-copy-v7.js",
    "assets/premium-preview-v7.css",
    "assets/home-dashboard.js",
    "assets/email-interest.js",
)
REQUIRED_EMAIL_ASSETS = (
    "assets/signup-email-intent.js",
    "assets/email-preferences.js",
    "assets/email-preferences.css",
    "assets/email-interest.js",
)
REQUIRED_HOME_FILES = (
    "assets/home-dashboard.css",
    "assets/home-density.css",
    "assets/home-dense-v3.css",
    "assets/home-focus-v1.css",
    "assets/home-core-v1.js",
    "assets/recommendation-dense-v3.css",
)
EXCLUDED_PUBLIC_ROUTES = (
    "co-phieu/demo1/index.html",
    "kien-thuc/index.html",
    "pro/index.html",
    "email/index.html",
    "theo-doi/index.html",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def base_href(source: str) -> str | None:
    match = re.search(r'<base\s+[^>]*href=["\']([^"\']+)["\']', source, flags=re.IGNORECASE)
    return match.group(1) if match else None


def is_homepage(page: Path, output: Path) -> bool:
    return page.resolve() == (output / "index.html").resolve()


def verify_asset(page: Path, output: Path, source: str, asset: str) -> str | None:
    pattern = rf'(?:href|src)=["\']([^"\']*{re.escape(Path(asset).name)}(?:\?[^"\']*)?)["\']'
    match = re.search(pattern, source, flags=re.IGNORECASE)
    if not match:
        return f"missing injected asset {asset}: {page.relative_to(output)}"
    reference = urlsplit(match.group(1)).path
    base = base_href(source)
    if base:
        if reference != asset:
            return f"base-relative asset path invalid on {page.relative_to(output)}: {reference} != {asset}"
    else:
        target = (page.parent / reference).resolve()
        if not target.is_file():
            return f"asset target missing on {page.relative_to(output)}: {reference}"
    return None


def verify_injected_assets(page: Path, output: Path, source: str) -> list[str]:
    errors: list[str] = []
    required = HOME_UX_ASSETS if is_homepage(page, output) else NON_HOME_UX_ASSETS
    for asset in required:
        error = verify_asset(page, output, source, asset)
        if error:
            errors.append(error)
    if is_homepage(page, output):
        for asset in HOMEPAGE_FORBIDDEN_ASSETS:
            if Path(asset).name in source:
                errors.append(f"homepage must not load legacy/heavy asset {asset}")
    return errors


def require_text(output: Path, relative_path: str, expected: tuple[str, ...], errors: list[str]) -> None:
    path = output / relative_path
    if not path.is_file():
        errors.append(f"required page missing: {relative_path}")
        return
    source = path.read_text(encoding="utf-8")
    for text in expected:
        if text not in source:
            errors.append(f"required production hook missing in {relative_path}: {text}")


def verify_header_auth_pair(page: Path, output: Path, source: str) -> list[str]:
    errors: list[str] = []
    if "site-header" not in source:
        return errors
    relative = page.relative_to(output)
    if source.count("data-header-auth-actions") != 1:
        errors.append(f"header must contain exactly one auth action group: {relative}")
    if "header-login-cta" not in source or "header-register-cta" not in source:
        errors.append(f"Login/Register header pair missing: {relative}")
    nav = re.search(r'<nav\b[^>]*data-nav-menu[^>]*>(.*?)</nav>', source, flags=re.IGNORECASE | re.DOTALL)
    if nav and re.search(r'href=["\'][^"\']*dang-(?:ky|nhap)/', nav.group(1), flags=re.IGNORECASE):
        errors.append(f"auth link remains in primary nav: {relative}")
    return errors


def main() -> None:
    output = parse_args().output.resolve()
    if not output.is_dir():
        raise RuntimeError(f"Pages output does not exist: {output}")

    errors: list[str] = []
    pages = sorted(output.rglob("*.html"))
    if not pages:
        errors.append("no HTML pages found")

    for route in EXCLUDED_PUBLIC_ROUTES:
        if (output / route).exists():
            errors.append(f"excluded route published: {route}")

    for asset in set((*HOME_UX_ASSETS, *NON_HOME_UX_ASSETS, *REQUIRED_EMAIL_ASSETS, *REQUIRED_HOME_FILES)):
        if not (output / asset).is_file():
            errors.append(f"required UX asset missing: {asset}")

    radar_tickers: list[str] = []
    universe_path = output / "public" / "data" / "ticker-universe.json"
    if not universe_path.is_file():
        errors.append("Radar review universe missing")
    else:
        payload = json.loads(universe_path.read_text(encoding="utf-8"))
        items = payload.get("items", [])
        counts = Counter(item.get("sector") for item in items)
        radar_tickers = [str(item.get("ticker") or "").upper() for item in items]
        if len(items) != 30:
            errors.append(f"Radar review must contain 30 tickers, got {len(items)}")
        if len(counts) != 10 or set(counts.values()) != {3}:
            errors.append(f"Radar review sector balance must be 10x3, got {dict(counts)}")
        if any(item.get("exchange") != "HOSE" for item in items):
            errors.append("Radar review contains non-HOSE ticker")

    require_text(output, "signup/index.html", ('name="email_daily_brief"', 'name="email_event_alerts"', 'assets/signup-email-intent.js'), errors)
    require_text(output, "tai-khoan/index.html", ('data-product-email-preferences', 'data-product-email-form', 'assets/email-preferences.js'), errors)
    require_text(
        output,
        "index.html",
        (
            'data-email-conversion', 'href="signup/"', 'href="dang-nhap/"', 'data-header-auth-actions',
            'assets/home-dense-v3.css', 'assets/home-focus-v1.css', 'assets/home-core-v1.js', 'assets/mobile-touch-v1.css',
            'home-radar-sector-list', 'home-tier-grid', 'co-phieu/ACB/', 'co-phieu/VNM/', 'co-phieu/NKG/', 'co-phieu/HAH/',
            'Radar 30', 'Phân tích doanh nghiệp', '4M · CANSLIM', 'Bear · Base · Bull',
            'Pivot · Breakout', 'Buy Zone · Stop · Target', '30 mã', '10 ngành · 3 mã mỗi ngành',
            'Free và Premium có gì?', 'Định giá Bear / Base / Bull', 'SEPA/VCP · Stage · Pivot',
            'VPA · RVOL · dòng tiền lớn', 'Email &amp; cảnh báo trong phiên', '4 mốc quét/ngày',
        ),
        errors,
    )
    home_source = (output / "index.html").read_text(encoding="utf-8") if (output / "index.html").is_file() else ""
    for obsolete in (
        "home-newsletter-strip", "Mã tham chiếu đang theo dõi được tách khỏi khuyến nghị đã phát hành.",
        "DỮ LIỆU HOSE THAM CHIẾU", "Danh sách cổ phiếu đang theo dõi", "home-watchlist-grid",
        "home-ticker-grid", "premium-preview-section", "MẪU BÁO CÁO CHUYÊN SÂU", "MẪU EMAIL GÓI TRẢ PHÍ",
        "Free bên trái · Premium bên phải", "Trạng thái công khai", "Chưa có setup", "đang hoàn thiện",
    ):
        if obsolete.lower() in home_source.lower():
            errors.append(f"obsolete homepage element remains: {obsolete}")

    if len(set(radar_tickers)) != 30:
        errors.append("Radar ticker routes require 30 unique public tickers")
    for ticker in radar_tickers:
        require_text(
            output,
            f"co-phieu/{ticker}/index.html",
            (
                '<base href="../../">',
                f'<title>{ticker} — Phân tích Free &amp; Premium | StockRadar</title>',
                f'<link rel="canonical" href="https://stockradar.vn/co-phieu/{ticker}/">',
                f'<meta property="og:url" content="https://stockradar.vn/co-phieu/{ticker}/">',
                f'data-static-ticker="{ticker}"',
                'name="robots" content="noindex,nofollow"',
                'assets/stock-page-context-v1.js',
            ),
            errors,
        )

    require_text(
        output,
        "dang-ky/index.html",
        (
            'data-header-auth-actions', 'href="dang-nhap/"', 'href="signup/"', 'data-email-interest-form',
            'name="daily_brief"', 'name="event_alerts"', 'assets/email-interest.js', 'assets/home-density.css',
            'assets/home-dense-v3.css', 'assets/site-v4.css', 'assets/public-ux.js', 'assets/public-fallbacks-v4.js',
            'assets/direct-ticker-nav-v1.js', 'assets/auth-production-gate.js', 'assets/public-copy-v7.js',
        ),
        errors,
    )
    require_text(
        output,
        "khuyen-nghi/index.html",
        (
            '<strong>0 mã</strong>', '<strong>30 mã</strong>', 'Danh sách cổ phiếu theo Radar rà soát',
            'reference-watch-table', '<b>ACB</b>', '<b>VNM</b>', '<b>NKG</b>', '<b>HAH</b>',
            'không phải khuyến nghị mua', 'assets/recommendation-dense-v3.css', 'assets/site-v4.css',
            'assets/public-ux.js', 'assets/public-fallbacks-v4.js', 'assets/direct-ticker-nav-v1.js',
            'assets/auth-production-gate.js', 'assets/public-copy-v7.js', 'data-header-auth-actions',
        ),
        errors,
    )

    for route in (
        "radar5/index.html", "breakout/index.html", "risk/index.html", "track-record/index.html",
        "thay-doi-hom-nay/index.html", "hieu-qua/index.html", "nganh/index.html",
        "kiem-tra-co-phieu/index.html", "phan-tich/index.html", "co-phieu/index.html",
    ):
        require_text(output, route, ('data-header-auth-actions', 'href="dang-nhap/"', 'href="signup/"', *NON_HOME_UX_ASSETS), errors)

    require_text(output, "quyen-rieng-tu/index.html", ('Đăng ký email trước khi xác minh tài khoản', 'tối đa 30 ngày'), errors)

    fallback_js = output / "assets" / "public-fallbacks-v4.js"
    if fallback_js.is_file():
        source = fallback_js.read_text(encoding="utf-8")
        for marker in (
            "radar-reference", "breakout-reference", "risk-reference", "today-reference",
            "performance-method", "track-method", "sector-reference", "lookup-reference",
            "report-reference", "referenceGrid", "sectorGrid", "enhanceNavigation", "TRẠNG THÁI DỮ LIỆU",
        ):
            if marker not in source:
                errors.append(f"full-site V4 fallback marker missing: {marker}")

    home_core = output / "assets" / "home-core-v1.js"
    if home_core.is_file():
        source = home_core.read_text(encoding="utf-8")
        for marker in ("emailDeliveryReady", "registrationUrl", "mountNavigation", "mountTickerSearch", "mountRegistration"):
            if marker not in source:
                errors.append(f"homepage core marker missing: {marker}")
        if "đang hoàn thiện" in source.lower():
            errors.append("homepage core contains unfinished-state copy")

    for page in pages:
        source = page.read_text(encoding="utf-8")
        upper = source.upper()
        for term in FORBIDDEN_PUBLIC_TERMS:
            if term in upper:
                errors.append(f"forbidden public term {term}: {page.relative_to(output)}")
        for term in FORBIDDEN_HTML_TERMS:
            if term in upper:
                errors.append(f"unfinished/internal HTML term {term}: {page.relative_to(output)}")
        errors.extend(verify_injected_assets(page, output, source))
        errors.extend(verify_header_auth_pair(page, output, source))

    for suffix in ("*.js", "*.json"):
        for path in output.rglob(suffix):
            upper = path.read_text(encoding="utf-8").upper()
            for term in FORBIDDEN_PUBLIC_TERMS:
                if term in upper:
                    errors.append(f"forbidden public term {term}: {path.relative_to(output)}")

    if errors:
        raise RuntimeError("Pages public-surface verification failed:\n- " + "\n- ".join(errors))

    print(f"Verified production public surface: {len(pages)} HTML pages; feature-first homepage + 30 static Radar ticker routes + concrete Free/Premium features present")


if __name__ == "__main__":
    main()