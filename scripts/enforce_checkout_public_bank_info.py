#!/usr/bin/env python3
"""Lock the live StockRadar Manual VietQR checkout in the final Pages artifact.

The private Supabase billing gate remains authoritative for creating and
confirming checkout requests. This build guard must never replace the live
payment surface with stale frontend commercial state.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

BANK_NAME = "VPBank"
ACCOUNT_NUMBER = "0934389822"
ACCOUNT_NAME = "NGUYỄN TỬ LINH"
STATIC_QR = "assets/vpbank-qr-static.svg?v=20260904-ownerqr1"


def expose_bank(source: str) -> str:
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
    source = source.replace(
        'QR trên chuyển đúng tới VPBank 0934389822 và số tiền 199.000đ.',
        'QR trên là mã tài khoản VPBank 0934389822 do chủ tài khoản cung cấp.',
    )
    source = source.replace(
        'QR VPBank hiển thị ngay. Đăng nhập để lấy mã SR riêng trước khi xác nhận chuyển khoản.',
        'QR VPBank hiển thị ngay. Đăng nhập để lấy số tiền 199.000đ và mã SR riêng trước khi chuyển khoản.',
    )

    required = (
        f'data-checkout-bank>{BANK_NAME}</strong>',
        f'data-checkout-account-number>{ACCOUNT_NUMBER}</strong>',
        f'data-checkout-account-name>{ACCOUNT_NAME}</strong>',
        f'data-copy-account data-copy-value="{ACCOUNT_NUMBER}"',
        'vpbank-qr-static.svg',
        'data-checkout-reference>—</strong>',
        'data-checkout-expiry>—</strong>',
    )
    for marker in required:
        if marker not in source:
            raise RuntimeError(f"Checkout production contract missing: {marker}")

    for forbidden in (
        'BẢO VỆ NGƯỜI DÙNG TRẢ PHÍ',
        'Premium tạm dừng kích hoạt mới',
        'data-checkout-ready="false"',
    ):
        if forbidden in source:
            raise RuntimeError(f"Stale paused checkout leaked into live artifact: {forbidden}")
    return source


def enforce(output: Path) -> Path:
    page = output / "thanh-toan" / "index.html"
    if not page.exists():
        raise FileNotFoundError(page)

    qr_asset = output / "assets" / "vpbank-qr-static.svg"
    if not qr_asset.is_file():
        raise RuntimeError(f"Missing fixed VPBank QR asset: {qr_asset}")

    source = expose_bank(page.read_text(encoding="utf-8"))
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
