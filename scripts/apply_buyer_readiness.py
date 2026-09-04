#!/usr/bin/env python3
"""Apply buyer-facing truth gates after the standard Pages UX injector.

This layer deliberately keeps product promises aligned with production capability:
- payment routes are not published until checkout is explicitly enabled;
- email delivery is not presented as active until delivery is explicitly enabled;
- Top HOSE / decision-card assets are injected on every public product surface.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path


def enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


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


def rewrite_capability_copy(source: str, *, email_ready: bool, checkout_ready: bool) -> str:
    if not checkout_ready:
        source = re.sub(
            r'href=["\'](?:\.\./)*thanh-toan/\?plan=premium["\']',
            'href="dang-ky/#premium-notify-title"',
            source,
            flags=re.IGNORECASE,
        )
        source = re.sub(
            r'href=["\'](?:\.\./)*thanh-toan/["\']',
            'href="dang-ky/#premium-notify-title"',
            source,
            flags=re.IGNORECASE,
        )
        for before, after in (
            ("Thanh toán / Nâng Premium", "Đăng ký quan tâm Premium"),
            ("Nâng Premium · 199K", "Tìm hiểu Premium"),
            ("Premium · 199.000đ", "Tìm hiểu Premium"),
            ("Đăng nhập để thanh toán", "Đăng nhập"),
        ):
            source = source.replace(before, after)

    if not email_ready:
        for before, after in (
            ("Nhận email 09:00", "Đăng ký"),
            ("Nhận bản tin 09:00 miễn phí", "Đăng ký Free"),
            ("FREE · EMAIL 09:00", "FREE · STOCKRADAR"),
            ("FREE 09:00 · PREMIUM TRONG PHIÊN", "TOP HOSE · RADAR · PHÂN TÍCH"),
            ("09:00 · Bản rà soát Free", "Top HOSE · StockRadar"),
            ("Free nhận bản tin 09:00.<br>Premium nhận cảnh báo trong phiên.", "Free để trải nghiệm.<br>Premium để phân tích sâu hơn."),
            ("Free: bản rà soát 09:00 · Premium: thêm cảnh báo điểm mua/bán trong phiên khi tín hiệu đủ chuẩn.", "Free: tra cứu và Radar · Premium: phân tích sâu, kế hoạch giao dịch và cảnh báo theo quyền gói."),
        ):
            source = source.replace(before, after)
    return source


def inject_assets(source: str, page: Path, output: Path) -> str:
    marker = "data-buyer-readiness-v1"
    if marker in source or "</head>" not in source:
        return source
    css = asset_href(source, page, output, "buyer-readiness-v1.css")
    js = asset_href(source, page, output, "buyer-readiness-v1.js")
    head = (
        f'<link rel="stylesheet" href="{css}?v=20260904-buyer1" {marker}>\n'
        f'<script src="{js}?v=20260904-buyer1" defer></script>\n'
    )
    return source.replace("</head>", head + "</head>", 1)


def main() -> None:
    output = parse_args().output.resolve()
    if not output.is_dir():
        raise RuntimeError(f"Pages output does not exist: {output}")

    email_ready = enabled("STOCKRADAR_PRODUCT_EMAIL_READY")
    checkout_ready = enabled("STOCKRADAR_CHECKOUT_READY")

    for required in ("buyer-readiness-v1.css", "buyer-readiness-v1.js"):
        if not (output / "assets" / required).is_file():
            raise RuntimeError(f"Missing buyer-readiness asset: {required}")

    if not checkout_ready:
        checkout = output / "thanh-toan"
        if checkout.exists():
            shutil.rmtree(checkout)

    pages = sorted(output.rglob("*.html"))
    for page in pages:
        source = page.read_text(encoding="utf-8")
        source = rewrite_capability_copy(source, email_ready=email_ready, checkout_ready=checkout_ready)
        source = inject_assets(source, page, output)
        page.write_text(source, encoding="utf-8")

    # Top ranking contract must always exist even when empty/fail-closed.
    top_contract = output / "public" / "data" / "top-stocks.json"
    if not top_contract.is_file():
        raise RuntimeError("Missing public Top HOSE contract: top-stocks.json")


if __name__ == "__main__":
    main()
