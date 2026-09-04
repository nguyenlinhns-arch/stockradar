#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED = (
    "PREMIUM · EMAIL 09:00",
    "Quan tâm Daily 09:00",
    "Tạo tài khoản Free",
    "Không bao gồm Daily 09:00 hoặc Action Alert",
    "Daily 09:00 theo watchlist",
)

STALE_FREE_EMAIL_PROMISES = (
    "FREE · EMAIL 09:00",
    "FREE 09:00",
    "Nhận bản tin 09:00 miễn phí",
    "Nhận bản rà soát thị trường mỗi sáng",
    "Nhận email 09:00 miễn phí",
    "kích hoạt bản tin 09:00",
    "bản rà soát 09:00 hằng ngày",
    "Tra cứu, Radar và bản rà soát 09:00",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> None:
    output = parse_args().output.resolve()
    home_path = output / "index.html"
    if not home_path.is_file():
        raise RuntimeError(f"homepage missing: {home_path}")

    home = home_path.read_text(encoding="utf-8")
    errors: list[str] = []

    for marker in REQUIRED:
        if marker not in home:
            errors.append(f"missing paid-only homepage marker: {marker}")

    for marker in STALE_FREE_EMAIL_PROMISES:
        if marker in home:
            errors.append(f"stale Free product-email promise remains: {marker}")

    if errors:
        raise RuntimeError("Paid-only homepage email verification failed:\n- " + "\n- ".join(errors))

    print("Paid-only homepage email verification: PASS")


if __name__ == "__main__":
    main()
