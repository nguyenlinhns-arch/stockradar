#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def require(source: str, markers: tuple[str, ...], label: str, errors: list[str]) -> None:
    for marker in markers:
        if marker not in source:
            errors.append(f"{label}: missing {marker}")


def main() -> None:
    output = parse_args().output.resolve()
    errors: list[str] = []

    home = (output / "index.html").read_text(encoding="utf-8")
    signup = (output / "signup" / "index.html").read_text(encoding="utf-8")
    account = (output / "tai-khoan" / "index.html").read_text(encoding="utf-8")

    require(home, (
        "data-premium-email-product-v1",
        "Không cần mở StockRadar liên tục",
        "09:00 · Watchlist trước",
        "Trong phiên · Chỉ khi đổi trạng thái",
        "Không đổi · Không spam",
        "Theo dõi mã của tôi &amp; nhận email",
        "Email chỉ được gửi khi tài khoản, consent, quyền gói và hệ thống delivery đều đủ điều kiện",
    ), "homepage Premium email", errors)

    require(signup, (
        "data-premium-email-onboarding",
        "Để StockRadar canh mã thay bạn",
        "Xác minh email StockRadar",
        "Thêm mã, khung đầu tư",
        "Bật Action Alert",
    ), "Premium email onboarding", errors)

    require(account, (
        "data-premium-email-health",
        "data-email-health-system",
        "data-email-health-watchlist",
        "data-email-health-tickers",
        "data-email-health-last",
        'name="post_session_digest"',
        'name="weekly_report"',
        "Không đổi trạng thái → không tạo Action Alert riêng",
    ), "My StockRadar email health", errors)

    for source, label in ((home, "home"), (signup, "signup"), (account, "account")):
        if "premium-email-product-v1.css" not in source:
            errors.append(f"{label}: Premium email stylesheet missing")

    asset = output / "assets" / "premium-email-product-v1.css"
    if not asset.is_file():
        errors.append("premium-email-product-v1.css missing")

    if errors:
        raise RuntimeError("Premium email product v1 verification failed:\n- " + "\n- ".join(errors))
    print("Premium email product v1 verification: PASS")


if __name__ == "__main__":
    main()
