#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> None:
    output = parse_args().output.resolve()
    home = output / "index.html"
    if not home.is_file():
        raise RuntimeError("Homepage missing")
    source = home.read_text(encoding="utf-8")
    errors: list[str] = []

    required = (
        "Bạn đang quan tâm mã nào?",
        "Tra mã miễn phí",
        "data-home-paid-intent-v1",
        "Đừng tự canh từng mã. Hãy để StockRadar theo dõi việc cần làm.",
        "data-home-intent-ticker",
        "MUA / CHỜ",
        "GIỮ / TĂNG / GIẢM / BÁN",
        "Vùng mua · Stop · Target",
        "KIỂM CHỨNG TRƯỚC KHI TRẢ TIỀN",
        "Có cả lãi và lỗ",
        "Không tính lệnh chưa kích hoạt",
        "So cùng VN-Index",
        "199.000đ",
        "Theo dõi mã của tôi",
        "data-premium-conversion-cta",
        "Xem email Premium 09:00",
        "Free chỉ nhận email hệ thống",
        "home-paid-intent-v1.css",
        "home-paid-intent-v1.js",
    )
    for marker in required:
        if marker not in source:
            errors.append(f"missing paid-intent homepage marker: {marker}")

    order = (
        "Bạn đang quan tâm mã nào?",
        "SAU KHI TRA MÃ",
        "KIỂM CHỨNG TRƯỚC KHI TRẢ TIỀN",
        "199.000đ",
        "Theo dõi mã của tôi",
    )
    try:
        positions = [source.index(marker) for marker in order]
        if positions != sorted(positions):
            errors.append("homepage paid journey order is wrong")
    except ValueError:
        pass

    obsolete = (
        "home-decision-v2",
        "home-focus-section",
        "home-tier-section",
        "home-conversion-band",
        "home-radar-sector-list",
        "home-tier-grid",
        "Full HOSE → Full-Scan Gate",
        "Action Gate",
        "production manifest",
        "quality gate",
        "BẠN ĐANG CẦN GÌ?",
        "Free và Premium có gì?",
    )
    for marker in obsolete:
        if marker.lower() in source.lower():
            errors.append(f"obsolete/technical homepage block remains: {marker}")

    forbidden_free_email = (
        "FREE · EMAIL 09:00",
        "FREE 09:00",
        "Nhận bản rà soát 09:00 miễn phí",
        "Nhận bản tin 09:00 miễn phí",
        "Xem bản rà soát Free",
        "tạo tài khoản Free và xác minh để kích hoạt bản tin 09:00",
        "nhận bản rà soát 09:00 miễn phí",
    )
    for marker in forbidden_free_email:
        if marker.casefold() in source.casefold():
            errors.append(f"Free product-email promise remains on homepage: {marker}")

    price_pos = source.find("199.000đ")
    proof_pos = source.find("KIỂM CHỨNG TRƯỚC KHI TRẢ TIỀN")
    if price_pos >= 0 and proof_pos >= 0 and price_pos < proof_pos:
        errors.append("Premium price appears before proof section")

    if errors:
        raise RuntimeError("Homepage paid-intent verification failed:\n- " + "\n- ".join(errors))
    print("Homepage paid-intent verification: PASS (lookup → personal need → proof → 199K CTA; Free email is transactional-only)")


if __name__ == "__main__":
    main()
