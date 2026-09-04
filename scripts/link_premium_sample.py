#!/usr/bin/env python3
"""Expose the truthful Premium sample from high-intent buyer surfaces."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> None:
    output = parse_args().output.resolve()

    stock = output / "co-phieu" / "index.html"
    if stock.is_file():
        source = stock.read_text(encoding="utf-8")
        needle = '<a class="button button-secondary" href="hieu-qua/" data-conversion-action="stock_proof">Xem hiệu quả trước</a>'
        sample = '<a class="button button-secondary" href="premium-mau/" data-conversion-action="stock_sample">Xem mẫu Premium</a>'
        if sample not in source and needle in source:
            source = source.replace(needle, sample + needle, 1)
        stock.write_text(source, encoding="utf-8")

    plans = output / "dang-ky" / "index.html"
    if plans.is_file():
        source = plans.read_text(encoding="utf-8")
        if 'data-conversion-action="plans_sample"' not in source:
            source, count = re.subn(
                r'(<a class="button button-primary"[^>]*data-conversion-action="plans_premium"[^>]*>.*?</a>)',
                r'\1<a class="button button-secondary" href="premium-mau/" data-conversion-action="plans_sample">Xem mẫu Premium</a>',
                source,
                count=1,
                flags=re.DOTALL,
            )
            if count != 1:
                raise RuntimeError("Premium pricing CTA not found for sample link")
        plans.write_text(source, encoding="utf-8")

    sample_page = output / "premium-mau" / "index.html"
    if not sample_page.is_file():
        raise RuntimeError("Premium sample route missing from Pages artifact")

    print("Premium sample links: PASS")


if __name__ == "__main__":
    main()
