"""Verify checkout starts closed; the authenticated backend owns payment details."""
import argparse
import re
from pathlib import Path

def enforce_live_checkout(source: str) -> str:
    # Retained entry point for build compatibility. Static environment flags never open payment.
    for marker in ('data-checkout-ready="false"', 'data-checkout-payment hidden',
                   'data-checkout-disabled-fallback', 'data-checkout-confirm', 'data-checkout-reference'):
        if marker not in source:
            raise RuntimeError(f"Fail-closed checkout contract missing: {marker}")
    if re.search(r'<img[^>]+data-checkout-qr-image[^>]+src=', source) or 'fallbackQr' in source:
        raise RuntimeError('Checkout exposes a QR before server readiness')
    if '0934389822' in source or 'QR hiển thị ngay' in source:
        raise RuntimeError('Checkout exposes static payment instructions')
    return source

def enforce(output: Path) -> Path:
    page = output / 'thanh-toan' / 'index.html'
    enforce_live_checkout(page.read_text(encoding='utf-8'))
    print('Premium checkout fail-closed: PASS (runtime backend authority)')
    return page

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    enforce(parser.parse_args().output)
