#!/usr/bin/env python3
"""Expose the production receiving bank on the final checkout artifact.

Bank identity is public checkout information. User-specific transfer reference,
VietQR payload and expiry remain session-bound and are generated only after login.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

BANK_NAME = "VPBank"
ACCOUNT_NUMBER = "0934389822"
ACCOUNT_NAME = "NGUYỄN TỬ LINH"


def enforce(output: Path) -> Path:
    page = output / "thanh-toan" / "index.html"
    if not page.exists():
        raise FileNotFoundError(page)

    source = page.read_text(encoding="utf-8")

    source = re.sub(
        r'<p>Đăng nhập để hệ thống cấp số tiền, mã giao dịch và thời hạn thanh toán\. Không dùng lại nội dung chuyển khoản của giao dịch cũ\.</p>',
        '<p>Tài khoản nhận tiền chính thức của StockRadar là VPBank · 0934389822 · NGUYỄN TỬ LINH. Đăng nhập để hệ thống tạo nội dung chuyển khoản riêng, QR và thời hạn thanh toán cho đúng tài khoản.</p>',
        source,
        count=1,
    )
    source = source.replace(
        '<span>Đăng nhập và tạo yêu cầu thanh toán để hiển thị QR.</span>',
        '<span>Đăng nhập để hệ thống tạo QR kèm nội dung chuyển khoản riêng.</span>',
        1,
    )
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

    required = (
        f'data-checkout-bank>{BANK_NAME}</strong>',
        f'data-checkout-account-number>{ACCOUNT_NUMBER}</strong>',
        f'data-checkout-account-name>{ACCOUNT_NAME}</strong>',
        f'data-copy-account data-copy-value="{ACCOUNT_NUMBER}"',
        'data-checkout-reference>—</strong>',
        'data-checkout-expiry>—</strong>',
        'Đăng nhập để hệ thống tạo QR kèm nội dung chuyển khoản riêng.',
    )
    for marker in required:
        if marker not in source:
            raise RuntimeError(f"Checkout public bank contract missing: {marker}")

    page.write_text(source, encoding="utf-8")
    print(f"Locked public checkout bank info: {page}")
    return page


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    enforce(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
