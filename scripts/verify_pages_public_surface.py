#!/usr/bin/env python3
"""Verify the generated GitHub Pages artifact is production-facing and decision-first.

Public publication is dynamic full-HOSE. Until licensed production data is approved, the
public ticker seed must remain fail-closed: no curated ticker list and no generated ticker
routes. The verifier protects that contract instead of requiring the retired Radar-30 demo.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit


FORBIDDEN_ASSET_TERMS = ("DEMO", "MOCK", "MÔ PHỎNG", "FIXTURE", "SHADOW")
FORBIDDEN_HTML_TERMS = (
    "DEMO", "MOCK", "MÔ PHỎNG", "FIXTURE",
    "DATA GATE", "CHƯA SẴN SÀNG", "CHƯA PHÁT HÀNH", "CHƯA CÓ SETUP",
    "ĐANG HOÀN THIỆN", "TRẠNG THÁI CÔNG KHAI", "ĐANG TẢI", "ĐANG KIỂM TRA",
    "CHỜ DỮ LIỆU", "DỮ LIỆU THAM CHIẾU", "MÃ THAM CHIẾU",
    "MẪU BÁO CÁO", "MẪU EMAIL", "DỮ LIỆU MẪU",
)
FORBIDDEN_PUBLIC_METHOD_TERMS = (
    "PHÂN TÍCH",
    "4M", "CANSLIM", "SEPA", "VCP", "VPA", "RVOL", "POCKET PIVOT",
    "EARLY BREAKOUT", "CONFIRMED BREAKOUT", "PAYBACK", "WYCKOFF", "MINERVINI",
    "O’NEIL", "O'NEIL", "PHIL TOWN", "BEAR/BASE/BULL", "BEAR · BASE · BULL",
    "BEAR / BASE / BULL",
)
HOME_UX_ASSETS = ("assets/mobile-touch-v1.css", "assets/home-core-v1.js")
NON_HOME_UX_ASSETS = (
    "assets/public-ux.css", "assets/site-v4.css", "assets/mobile-touch-v1.css",
    "assets/public-ux.js", "assets/public-fallbacks-v4.js", "assets/direct-ticker-nav-v1.js",
    "assets/auth-production-gate.js", "assets/header-auth-dedupe-v6.js", "assets/public-copy-v7.js",
)
HOMEPAGE_FORBIDDEN_ASSETS = (
    "assets/app.js", "assets/home-dashboard.css", "assets/site-v4.css", "assets/public-ux.css",
    "assets/public-ux.js", "assets/public-fallbacks-v4.js", "assets/direct-ticker-nav-v1.js",
    "assets/auth-production-gate.js", "assets/header-auth-dedupe-v6.js", "assets/public-copy-v7.js",
    "assets/premium-preview-v7.css", "assets/home-dashboard.js", "assets/email-interest.js",
)
REQUIRED_EMAIL_ASSETS = (
    "assets/signup-email-intent.js", "assets/email-preferences.js", "assets/email-preferences.css", "assets/email-interest.js",
)
REQUIRED_HOME_FILES = (
    "assets/home-dashboard.css", "assets/home-density.css", "assets/home-dense-v3.css",
    "assets/home-focus-v1.css", "assets/home-core-v1.js", "assets/recommendation-dense-v3.css",
)
EXCLUDED_PUBLIC_ROUTES = (
    "co-phieu/demo1/index.html", "kien-thuc/index.html", "pro/index.html", "email/index.html", "theo-doi/index.html",
    "phan-tich/index.html",
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


def verify_fail_closed_universe(output: Path, errors: list[str]) -> None:
    universe_path = output / "public" / "data" / "ticker-universe.json"
    if not universe_path.is_file():
        errors.append("public ticker universe missing")
        return
    payload = json.loads(universe_path.read_text(encoding="utf-8"))
    if payload.get("data_status") != "BLOCKED_DATA_GATE":
        errors.append(f"public ticker seed must be fail-closed, got data_status={payload.get('data_status')}")
    if payload.get("public_scope") != "FAIL_CLOSED_NO_PUBLIC_TICKER_SEED":
        errors.append(f"public ticker seed scope is not fail-closed: {payload.get('public_scope')}")
    if payload.get("items") != []:
        errors.append("fail-closed public ticker seed must contain zero public ticker rows")
    internal = payload.get("internal_reference") or {}
    if int(internal.get("record_count") or 0) <= 0:
        errors.append("fail-closed ticker contract lost internal reference count")
    if internal.get("raw_publication_allowed") is not False:
        errors.append("raw public ticker publication must remain disabled")

    co_phieu = output / "co-phieu"
    if co_phieu.is_dir():
        generated = sorted(
            path.parent.name
            for path in co_phieu.glob("*/index.html")
            if path.parent.name != "demo1"
        )
        if generated:
            errors.append("fail-closed Pages artifact generated fixed ticker routes: " + ", ".join(generated))


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

    verify_fail_closed_universe(output, errors)

    require_text(output, "signup/index.html", ('name="email_daily_brief"', 'name="email_event_alerts"', 'assets/signup-email-intent.js'), errors)
    require_text(output, "tai-khoan/index.html", ('data-product-email-preferences', 'data-product-email-form', 'assets/email-preferences.js'), errors)
    require_text(
        output, "index.html",
        (
            'data-email-conversion', 'href="signup/"', 'href="dang-nhap/"', 'data-header-auth-actions',
            'assets/home-dense-v3.css', 'assets/home-focus-v1.css', 'assets/home-core-v1.js', 'assets/mobile-touch-v1.css',
            'home-radar-sector-list', 'home-tier-grid', 'Bạn đang quan tâm mã nào?', 'Tra mã miễn phí',
            'home-decision-v2', 'Free và Premium có gì?', 'Lý do chính', 'Biên an toàn &amp; kỳ vọng',
            'Trạng thái giá', 'Dòng tiền &amp; rủi ro', 'Email & cảnh báo trong phiên', '4 mốc/ngày',
        ), errors,
    )
    home_source = (output / "index.html").read_text(encoding="utf-8") if (output / "index.html").is_file() else ""
    for obsolete in (
        "home-newsletter-strip", "Mã tham chiếu đang theo dõi được tách khỏi khuyến nghị đã phát hành.",
        "DỮ LIỆU HOSE THAM CHIẾU", "Danh sách cổ phiếu đang theo dõi", "home-watchlist-grid", "home-ticker-grid",
        "premium-preview-section", "MẪU BÁO CÁO CHUYÊN SÂU", "MẪU EMAIL GÓI TRẢ PHÍ",
        "Free bên trái · Premium bên phải", "Trạng thái công khai", "Chưa có setup", "đang hoàn thiện",
        "home-status-band", "home-status-grid",
    ):
        if obsolete.lower() in home_source.lower():
            errors.append(f"obsolete homepage element remains: {obsolete}")

    require_text(
        output, "dang-ky/index.html",
        (
            'data-header-auth-actions', 'href="dang-nhap/"', 'href="signup/?plan=free"', 'href="signup/?plan=premium"',
            'data-proposition="plans"', 'data-plan-free', 'data-plan-premium', 'data-plan-comparison', 'assets/plans-v1.css',
            'assets/site-v4.css', 'assets/public-ux.js', 'assets/public-fallbacks-v4.js', 'assets/direct-ticker-nav-v1.js',
            'assets/auth-production-gate.js', 'assets/public-copy-v7.js', 'conversion-plan-card', '199.000đ', 'Xem mẫu Premium',
        ), errors,
    )
    require_text(
        output, "khuyen-nghi/index.html",
        (
            'data-current-action-count', 'Toàn HOSE', 'Shortlist theo snapshot', 'reference-watch-table',
            'data-radar-review-list', 'Không đủ chuẩn → không công bố', 'assets/recommendation-dense-v3.css',
            'assets/site-v4.css', 'assets/public-ux.js', 'assets/public-fallbacks-v4.js', 'assets/direct-ticker-nav-v1.js',
            'assets/auth-production-gate.js', 'assets/public-copy-v7.js', 'data-header-auth-actions',
        ), errors,
    )

    route_features = {
        "radar5/index.html": ('CÁCH DÙNG RADAR', '3. Xem trạng thái', '4. Quản trị rủi ro'),
        "breakout/index.html": ('Mua · chờ · theo dõi · bỏ qua', 'TRẠNG THÁI HÀNH ĐỘNG'),
        "risk/index.html": ('Stop-loss · Hạ tỷ trọng · Cắt lỗ · Risk/Reward', '4 MỐC QUÉT TRONG PHIÊN'),
        "track-record/index.html": ('Dấu thời gian · Entry · Target/Stop · Vòng đời khuyến nghị', 'NHẬT KÝ APPEND-ONLY'),
        "thay-doi-hom-nay/index.html": ('Trạng thái · Vùng giá · Dòng tiền · Thị trường', '4 MỐC QUÉT TRONG PHIÊN'),
        "hieu-qua/index.html": ('Kích hoạt · Entry · Target/Stop · Benchmark', 'KẾT QUẢ TRƯỚC, CÁCH ĐO SAU', 'data-performance-summary'),
        "nganh/index.html": ('SO SÁNH CÙNG NGÀNH',),
        "kiem-tra-co-phieu/index.html": ('TOÀN HOSE · 4 KHUNG', 'Buy Zone · Stop · Target'),
        "co-phieu/index.html": ('Mã này nên làm gì?', 'BẢN XEM TRƯỚC PREMIUM', 'MUA / CHỜ', 'GIỮ / TĂNG / GIẢM / BÁN', 'Vùng mua', 'Target', 'Xem mẫu Premium'),
        "premium-mau/index.html": ('MẪU GIAO DIỆN · KHÔNG PHẢI KHUYẾN NGHỊ', 'MUA / CHỜ', 'GIỮ / TĂNG / GIẢM / BÁN', '[Theo snapshot thật]'),
    }
    for route, features in route_features.items():
        require_text(output, route, ('data-header-auth-actions', 'href="dang-nhap/"', 'href="dang-ky/"', *NON_HOME_UX_ASSETS, *features), errors)

    require_text(output, "quyen-rieng-tu/index.html", ('Đăng ký email trước khi xác minh tài khoản', 'tối đa 30 ngày'), errors)

    fallback_js = output / "assets" / "public-fallbacks-v4.js"
    if fallback_js.is_file():
        source = fallback_js.read_text(encoding="utf-8")
        for marker in (
            "radar-reference", "breakout-reference", "risk-reference", "today-reference", "performance-method",
            "track-method", "sector-reference", "lookup-reference", "report-reference", "referenceGrid", "sectorGrid",
            "featureGrid", "hideBlockedSurface", "enhanceNavigation", "TÍNH NĂNG STOCKRADAR",
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

    auth_gate = output / "assets" / "auth-production-gate.js"
    if auth_gate.is_file():
        source = auth_gate.read_text(encoding="utf-8").lower()
        for phrase in ("đang hoàn thiện", "tạm khóa", "chờ email xác minh"):
            if phrase in source:
                errors.append(f"auth gate exposes unfinished-state copy: {phrase}")

    for page in pages:
        source = page.read_text(encoding="utf-8")
        upper = source.upper()
        for term in FORBIDDEN_HTML_TERMS:
            if term in upper:
                errors.append(f"unfinished/fake-data public HTML term {term}: {page.relative_to(output)}")
        for term in FORBIDDEN_PUBLIC_METHOD_TERMS:
            if term in upper:
                errors.append(f"analysis/method language leaked to public HTML {term}: {page.relative_to(output)}")
        if re.search(r'href=["\'][^"\']*phan-tich/', source, flags=re.IGNORECASE):
            errors.append(f"legacy analysis route link remains: {page.relative_to(output)}")
        errors.extend(verify_injected_assets(page, output, source))
        errors.extend(verify_header_auth_pair(page, output, source))

    for suffix in ("*.js", "*.json"):
        for path in output.rglob(suffix):
            upper = path.read_text(encoding="utf-8").upper()
            for term in FORBIDDEN_ASSET_TERMS:
                if term in upper:
                    errors.append(f"forbidden fake-data term {term}: {path.relative_to(output)}")

    if errors:
        raise RuntimeError("Pages public-surface verification failed:\n- " + "\n- ".join(errors))

    print(
        f"Verified production public surface: {len(pages)} HTML pages; dynamic full-HOSE contract fail-closed; no fixed public ticker seed/routes; /phan-tich/ retired; no analysis labels, named methods/setup jargon or fake-data copy"
    )


if __name__ == "__main__":
    main()
