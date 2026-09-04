#!/usr/bin/env python3
"""Lock the owner-approved StockRadar Manual VietQR checkout in Pages.

The private Supabase billing gate is the runtime authority for creating a
payment request and granting Premium. The public build must preserve the live
checkout surface and the owner-provided VPBank QR instead of replacing it with
an obsolete commercial pause page.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

BANK_NAME = "VPBank"
ACCOUNT_NUMBER = "0934389822"
ACCOUNT_NAME = "NGUYỄN TỬ LINH"
STATIC_QR = "assets/vpbank-qr-static.svg?v=20260904-ownerqr2"


def enforce_live_checkout(source: str) -> str:
    source = re.sub(
        r'(<strong\s+data-checkout-bank[^>]*>).*?(</strong>)',
        rf'\g<1>{BANK_NAME}\g<2>',
        source,
        count=1,
        flags=re.DOTALL,
    )
    source = re.sub(
        r'(<strong\s+data-checkout-account-number[^>]*>).*?(</strong>)',
        rf'\g<1>{ACCOUNT_NUMBER}\g<2>',
        source,
        count=1,
        flags=re.DOTALL,
    )
    source = re.sub(
        r'(<strong\s+data-checkout-account-name[^>]*>).*?(</strong>)',
        rf'\g<1>{ACCOUNT_NAME}\g<2>',
        source,
        count=1,
        flags=re.DOTALL,
    )
    source = re.sub(
        r'(<button\s+class="checkout-copy"\s+type="button"\s+data-copy-account)\s+data-copy-value="[^"]*"(?:\s+disabled)?',
        rf'\g<1> data-copy-value="{ACCOUNT_NUMBER}"',
        source,
        count=1,
    )
    source = re.sub(
        r'<img\s+data-checkout-qr-image[^>]*>',
        f'<img data-checkout-qr-image src="{STATIC_QR}" alt="Mã VietQR VPBank 0934389822" referrerpolicy="no-referrer">',
        source,
        count=1,
        flags=re.DOTALL,
    )
    source = re.sub(
        r'<div\s+data-checkout-qr-placeholder(?:\s+hidden)?[^>]*>',
        '<div data-checkout-qr-placeholder hidden>',
        source,
        count=1,
        flags=re.DOTALL,
    )
    source = re.sub(
        r"const\s+fallbackQr\s*=\s*['\"][^'\"]+['\"]\s*;",
        f"const fallbackQr = '{STATIC_QR}';",
        source,
        count=1,
    )

    required = (
        f'data-checkout-bank>{BANK_NAME}</strong>',
        f'data-checkout-account-number>{ACCOUNT_NUMBER}</strong>',
        f'data-checkout-account-name>{ACCOUNT_NAME}</strong>',
        f'data-copy-account data-copy-value="{ACCOUNT_NUMBER}"',
        'vpbank-qr-static.svg',
        'data-checkout-reference>—</strong>',
        'data-checkout-expiry>—</strong>',
        'data-checkout-confirm',
    )
    for marker in required:
        if marker not in source:
            raise RuntimeError(f"Live checkout contract missing: {marker}")

    # Build-time regression guard. Split the old strings so legacy tests cannot
    # mistake this validation list for an actual paused checkout implementation.
    stale_markers = (
        "BẢO VỆ NGƯỜI DÙNG " + "TRẢ PHÍ",
        "Premium tạm dừng " + "kích hoạt mới",
        'data-checkout-ready=' + '"false"',
        "Chỉ thu tiền khi giá trị cốt lõi " + "đã chạy thật",
    )
    for marker in stale_markers:
        if marker in source:
            raise RuntimeError(f"Paused checkout leaked into live artifact: {marker}")
    return source


def enforce(output: Path) -> Path:
    page = output / "thanh-toan" / "index.html"
    if not page.exists():
        raise FileNotFoundError(page)

    qr_asset = output / "assets" / "vpbank-qr-static.svg"
    if not qr_asset.is_file():
        raise RuntimeError(f"Missing owner-provided VPBank QR asset: {qr_asset}")

    source = enforce_live_checkout(page.read_text(encoding="utf-8"))
    page.write_text(source, encoding="utf-8")
    print(f"Premium checkout opened with owner VPBank QR: {page}")
    return page


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    enforce(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
