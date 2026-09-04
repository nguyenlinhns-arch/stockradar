#!/usr/bin/env python3
"""Verify the production Pages artifact has the conversion-first buyer journey."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def read(output: Path, route: str = "") -> str:
    path = output / route / "index.html" if route else output / "index.html"
    if not path.is_file():
        raise RuntimeError(f"Missing route: {path}")
    return path.read_text(encoding="utf-8")


def require(source: str, *markers: str, label: str) -> None:
    missing = [marker for marker in markers if marker not in source]
    if missing:
        raise RuntimeError(f"{label} missing: {', '.join(missing)}")


def main() -> None:
    output = parse_args().output.resolve()
    home = read(output)
    require(
        home,
        "Bạn đang quan tâm mã nào?",
        "Tra mã miễn phí",
        "conversion-search-only",
        "Không cần tài khoản chứng khoán",
        "home-decision-v2",
        label="homepage conversion",
    )
    if "buyer-start-card" in home:
        raise RuntimeError("Homepage still has competing buyer-start CTA above the fold")

    stock = read(output, "co-phieu")
    require(
        stock,
        "BẢN XEM TRƯỚC PREMIUM",
        "Mở quyết định đầy đủ cho mã bạn vừa tra",
        "MUA / CHỜ",
        "GIỮ / TĂNG / GIẢM / BÁN",
        "Vùng mua",
        "Stop / vô hiệu",
        "Target",
        "data-premium-conversion-cta",
        "data-premium-stock-report",
        "data-premium-gate-copy",
        label="stock premium preview",
    )

    plans = read(output, "dang-ky")
    require(
        plans,
        "Bốn thứ trực tiếp giúp bạn ra quyết định",
        "1 · Quyết định",
        "2 · Vùng hành động",
        "3 · Cảnh báo",
        "4 · Kiểm chứng",
        "199.000đ",
        "conversion-plan-card",
        label="pricing conversion",
    )
    if "299.000" in plans:
        raise RuntimeError("Pricing still exposes an unverified 299K anchor")

    signup = read(output, "signup")
    require(
        signup,
        "conversion-premium-summary",
        "data-premium-flow-summary",
        "Tùy chọn nhận email",
        "conversion-v3.js",
        label="signup conversion",
    )

    performance = read(output, "hieu-qua")
    require(
        performance,
        "KẾT QUẢ TRƯỚC, CÁCH ĐO SAU",
        "Hãy nhìn dữ liệu thực tế trước khi quyết định trả phí",
        "data-performance-summary",
        label="performance conversion",
    )
    if performance.index("conversion-performance-head") > performance.index("BẰNG CHỨNG TRƯỚC KHI TRẢ PHÍ"):
        raise RuntimeError("Performance explanation still appears before the actual-result surface")

    account = read(output, "tai-khoan")
    require(
        account,
        "My StockRadar",
        "Biến watchlist thành trung tâm quyết định cá nhân",
        "Cảnh báo từng mã",
        "ƯU TIÊN THEO DÕI",
        label="account conversion",
    )

    recommendations = read(output, "khuyen-nghi")
    require(
        recommendations,
        "Muốn nhận các thay đổi này cho chính watchlist của bạn?",
        "data-premium-conversion-cta",
        label="recommendation conversion",
    )

    for asset in ("conversion-v3.css", "conversion-v3.js"):
        if not (output / "assets" / asset).is_file():
            raise RuntimeError(f"Missing production asset: {asset}")

    print("Conversion v3 verifier: PASS")


if __name__ == "__main__":
    main()
