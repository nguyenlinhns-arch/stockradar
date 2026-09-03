#!/usr/bin/env python3
"""Verify the generated GitHub Pages artifact is production-facing and self-contained."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import urlsplit


FORBIDDEN_PUBLIC_TERMS = ("DEMO", "MOCK", "MÔ PHỎNG", "FIXTURE", "SHADOW")
FORBIDDEN_HTML_TERMS = ("DATA GATE",)
REQUIRED_UX_ASSETS = (
    "assets/public-ux.css",
    "assets/public-ux.js",
    "assets/auth-production-gate.js",
)
REQUIRED_EMAIL_ASSETS = (
    "assets/signup-email-intent.js",
    "assets/email-preferences.js",
    "assets/email-preferences.css",
    "assets/email-interest.js",
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

    for asset in (*REQUIRED_UX_ASSETS, *REQUIRED_EMAIL_ASSETS):
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
            'data-email-interest-form',
            'name="daily_brief"',
            'name="event_alerts"',
            'assets/email-interest.js',
            'Đăng ký nhận email',
            'chờ xác minh',
        ),
        errors,
    )
    require_text(
        output,
        "quyen-rieng-tu/index.html",
        ('Đăng ký email trước khi xác minh tài khoản', 'tối đa 30 ngày'),
        errors,
    )

    for page in pages:
        source = page.read_text(encoding="utf-8")
        upper = source.upper()
        for term in FORBIDDEN_PUBLIC_TERMS:
            if term in upper:
                errors.append(f"forbidden public term {term}: {page.relative_to(output)}")
        for term in FORBIDDEN_HTML_TERMS:
            if term in upper:
                errors.append(f"internal HTML term {term}: {page.relative_to(output)}")
        errors.extend(verify_injected_assets(page, output, source))

    for suffix in ("*.js", "*.json"):
        for path in output.rglob(suffix):
            upper = path.read_text(encoding="utf-8").upper()
            for term in FORBIDDEN_PUBLIC_TERMS:
                if term in upper:
                    errors.append(f"forbidden public term {term}: {path.relative_to(output)}")

    if errors:
        raise RuntimeError("Pages public-surface verification failed:\n- " + "\n- ".join(errors))

    print(f"Verified production public surface: {len(pages)} HTML pages; email registration funnel present")


if __name__ == "__main__":
    main()
