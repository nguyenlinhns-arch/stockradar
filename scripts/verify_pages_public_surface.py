#!/usr/bin/env python3
"""Verify the generated GitHub Pages artifact is production-facing and self-contained."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import urlsplit


FORBIDDEN_PUBLIC_TERMS = ("DEMO", "MOCK", "MÔ PHỎNG", "FIXTURE", "SHADOW")
FORBIDDEN_HTML_TERMS = ("DATA GATE", "CHƯA SẴN SÀNG", "CHƯA PHÁT HÀNH")
REQUIRED_UX_ASSETS = (
    "assets/public-ux.css",
    "assets/public-ux.js",
    "assets/auth-production-gate.js",
    "assets/site-v4.css",
    "assets/public-fallbacks-v4.js",
    "assets/header-auth-dedupe-v6.js",
    "assets/public-copy-v7.js",
)
REQUIRED_EMAIL_ASSETS = (
    "assets/signup-email-intent.js",
    "assets/email-preferences.js",
    "assets/email-preferences.css",
    "assets/email-interest.js",
)
REQUIRED_HOME_ASSETS = (
    "assets/home-dashboard.js",
    "assets/home-dashboard.css",
    "assets/home-density.css",
    "assets/home-dense-v3.css",
    "assets/recommendation-dense-v3.css",
    "assets/premium-preview-v7.css",
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


def verify_injected_assets(page: Path, output: Path, source: str) -> list[str]:
    errors: list[str] = []
    base = base_href(source)
    for asset in REQUIRED_UX_ASSETS:
        pattern = rf'(?:href|src)=["\']([^"\']*{re.escape(Path(asset).name)}(?:\?[^"\']*)?)["\']'
        match = re.search(pattern, source, flags=re.IGNORECASE)
        if not match:
            errors.append(f"missing injected asset {asset}: {page.relative_to(output)}")
            continue
        reference = urlsplit(match.group(1)).path
        if base:
            if reference != asset:
                errors.append(
                    f"base-relative asset path invalid on {page.relative_to(output)}: {reference} != {asset}"
                )
        else:
            target = (page.parent / reference).resolve()
            if not target.is_file():
                errors.append(f"asset target missing on {page.relative_to(output)}: {reference}")
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

    for asset in (*REQUIRED_UX_ASSETS, *REQUIRED_EMAIL_ASSETS, *REQUIRED_HOME_ASSETS):
        if not (output / asset).is_file():
            errors.append(f"required UX asset missing: {asset}")

    require_text(
        output,
        "signup/index.html",
        ('name="email_daily_brief"', 'name="email_event_alerts"', 'assets/signup-email-intent.js'),
        errors,
    )
    require_text(
        output,
        "tai-khoan/index.html",
        ('data-product-email-preferences', 'data-product-email-form', 'assets/email-preferences.js'),
        errors,
    )
    require_text(
        output,
        "index.html",
        (
            'data-email-conversion',
            'href="dang-ky/"',
            'href="dang-nhap/"',
            'data-header-auth-actions',
            'assets/home-dense-v3.css',
            'assets/premium-preview-v7.css',
            'assets/site-v4.css',
            'assets/public-fallbacks-v4.js',
            'assets/public-copy-v7.js',
            'home-watchlist-grid',
            'home-ticker-grid',
            '<b>ACB</b>',
            '<b>VNM</b>',
            'Tín hiệu hành động hiện tại',
            '<strong>0 mã</strong>',
            'Danh sách cổ phiếu đang theo dõi',
            '<strong>16 mã</strong>',
            'MẪU BÁO CÁO CHUYÊN SÂU',
            '4M &amp; Payback Time',
            'Định giá Bear / Base / Bull',
            'MẪU EMAIL GÓI TRẢ PHÍ',
            'TOP 30 STOCKRADAR',
            '[StockRadar Premium] TOP 30 HOSE',
            'assets/home-dashboard.js',
        ),
        errors,
    )
    home_source = (output / "index.html").read_text(encoding="utf-8") if (output / "index.html").is_file() else ""
    if "home-newsletter-strip" in home_source:
        errors.append("homepage top newsletter strip must be removed")
    if "Mã tham chiếu đang theo dõi được tách khỏi khuyến nghị đã phát hành." in home_source:
        errors.append("obsolete homepage recommendation/reference sentence remains")
    if "DỮ LIỆU HOSE THAM CHIẾU" in home_source:
        errors.append("obsolete HOSE reference section remains on homepage")

    require_text(
        output,
        "dang-ky/index.html",
        (
            'Đăng ký nhận bản tin chứng khoán mỗi ngày từ StockRadar.vn',
            'data-header-auth-actions',
            'href="dang-nhap/"',
            'href="dang-ky/"',
            'data-email-interest-form',
            'name="daily_brief"',
            'name="event_alerts"',
            'assets/email-interest.js',
            'assets/home-density.css',
            'assets/home-dense-v3.css',
            'assets/site-v4.css',
        ),
        errors,
    )
    require_text(
        output,
        "khuyen-nghi/index.html",
        (
            '<strong>0 mã</strong>',
            '<strong>16 mã</strong>',
            'reference-watch-table',
            '<b>ACB</b>',
            '<b>VNM</b>',
            'không phải khuyến nghị mua',
            'assets/recommendation-dense-v3.css',
            'assets/site-v4.css',
            'data-header-auth-actions',
        ),
        errors,
    )

    for route in (
        "radar5/index.html",
        "breakout/index.html",
        "risk/index.html",
        "track-record/index.html",
        "thay-doi-hom-nay/index.html",
        "hieu-qua/index.html",
        "nganh/index.html",
        "kiem-tra-co-phieu/index.html",
        "phan-tich/index.html",
        "co-phieu/index.html",
    ):
        require_text(
            output,
            route,
            ('data-header-auth-actions', 'href="dang-nhap/"', 'href="dang-ky/"', 'assets/site-v4.css', 'assets/public-fallbacks-v4.js', 'assets/public-copy-v7.js'),
            errors,
        )

    require_text(
        output,
        "quyen-rieng-tu/index.html",
        ('Đăng ký email trước khi xác minh tài khoản', 'tối đa 30 ngày'),
        errors,
    )

    fallback_js = output / "assets" / "public-fallbacks-v4.js"
    if fallback_js.is_file():
        source = fallback_js.read_text(encoding="utf-8")
        for marker in (
            "radar-reference", "breakout-reference", "risk-reference", "today-reference",
            "performance-method", "track-method", "sector-reference", "lookup-reference",
            "report-reference", "referenceGrid", "sectorGrid", "enhanceNavigation",
            "TRẠNG THÁI DỮ LIỆU",
        ):
            if marker not in source:
                errors.append(f"full-site V4 fallback marker missing: {marker}")

    copy_v7 = output / "assets" / "public-copy-v7.js"
    if copy_v7.is_file():
        source = copy_v7.read_text(encoding="utf-8")
        for marker in ("CHƯA SẴN SÀNG", "CHƯA PHÁT HÀNH", "ĐANG CẬP NHẬT", "MutationObserver"):
            if marker not in source:
                errors.append(f"public copy V7 marker missing: {marker}")

    site_css = output / "assets" / "site-v4.css"
    if site_css.is_file():
        source = site_css.read_text(encoding="utf-8")
        for marker in (
            ".v4-reference-grid", ".v4-sector-grid", ".v4-zero-bar",
            ".header-auth-actions", ".header-login-cta", ".header-register-cta",
            "@media(max-width:760px)",
        ):
            if marker not in source:
                errors.append(f"full-site V4 CSS marker missing: {marker}")

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

    print(
        f"Verified production public surface: {len(pages)} HTML pages; "
        "premium previews + polished public wording + single Login/Register header pair present"
    )


if __name__ == "__main__":
    main()
