#!/usr/bin/env python3
"""Final commercial cleanup pass.

Removes residual explanatory copy from conversion-critical and dashboard routes while
preserving functional forms, data hooks, billing/auth controls and action outputs.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROUTES = ("signup", "dang-ky", "thanh-toan", "hieu-qua", "tai-khoan", "hom-nay", "khuyen-nghi")


def read(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"Missing commercial cleanup route: {path}")
    return path.read_text(encoding="utf-8")


def remove_block_by_class(source: str, class_name: str) -> str:
    pattern = re.compile(
        rf'\s*<(?:section|article|div)\b[^>]*class=["\'][^"\']*\b{re.escape(class_name)}\b[^"\']*["\'][^>]*>.*?</(?:section|article|div)>\s*',
        flags=re.I | re.S,
    )
    return pattern.sub("\n", source, count=1)


def cleanup_signup(source: str) -> str:
    # Marketing/onboarding explanation is redundant with plan selection and account page.
    source = remove_block_by_class(source, "premium-email-onboarding-v1")
    source = source.replace("Free 10 câu AI/ngày · Premium không giới hạn.", "Free 10 câu/ngày · Premium không giới hạn.")
    source = source.replace("Có thể bật/tắt từng loại email.", "Email Premium là tùy chọn.")
    return source


def cleanup_plans(source: str) -> str:
    source = re.sub(
        r'<p class="plan-price-note">.*?</p>',
        '<p class="plan-price-note">* Email Premium được bật khi kênh gửi chính thức sẵn sàng.</p>',
        source,
        count=1,
        flags=re.I | re.S,
    )
    source = re.sub(
        r'<p class="plan-legal">.*?</p>',
        '<p class="plan-legal">199K/30 ngày · Không tự gia hạn · Kích hoạt sau khi thanh toán được xác minh.</p>',
        source,
        count=1,
        flags=re.I | re.S,
    )
    return source


def cleanup_checkout(source: str) -> str:
    source = source.replace("Tài khoản nhận tiền vẫn là VPBank 0934389822", "Chưa có mã SR")
    source = source.replace(
        "Nếu hệ thống tạm thời chưa tạo được mã SR riêng, chưa chuyển khoản cho đến khi mã được hiển thị. Điều này giúp StockRadar đối soát đúng tài khoản Premium.",
        "Chỉ chuyển khoản khi mã SR đã hiển thị.",
    )
    return source


def cleanup_performance(source: str) -> str:
    source = source.replace("Không cherry-pick", "Mẫu thực tế")
    source = source.replace("Chưa kích hoạt ≠ đã mua", "Chưa kích hoạt ≠ giao dịch")
    source = source.replace("So cùng VN-Index", "So với VN-Index")
    source = source.replace("Có dấu thời gian", "Có thời gian")
    source, count = re.subn(
        r'<div class="conversion-performance-head">.*?</div><div data-performance-summary>',
        '<div class="conversion-performance-head"><h2>Kết quả thực tế</h2></div><div data-performance-summary>',
        source,
        count=1,
        flags=re.I | re.S,
    )
    if count != 1:
        raise RuntimeError("Performance explainer block not found")
    return source


def cleanup_account(source: str) -> str:
    source = source.replace(
        "Chỉ hiển thị metadata vận hành của chính tài khoản; không hiển thị provider secret hoặc nội dung email.",
        "Chỉ hiển thị trạng thái của tài khoản này.",
    )
    source = source.replace("Theo dõi đúng thứ bạn quan tâm", "Danh sách theo dõi")
    source = source.replace("Có thể nhập giá vốn và tỷ trọng ước tính nếu muốn cá nhân hóa sâu hơn.", "Giá vốn và tỷ trọng là tùy chọn.")
    source = source.replace("Có thể bật cảnh báo trên từng mã.", "Bật cảnh báo trên từng mã nếu cần.")
    return source


def cleanup_today(source: str) -> str:
    source = source.replace("Bảng Hôm nay hiển thị theo trạng thái tài khoản đã xác định.", "Đang tải…")
    source = source.replace(
        "StockRadar sẽ ưu tiên mã đang sở hữu, watchlist và cảnh báo đã bật trên chính tài khoản của bạn.",
        "Ưu tiên mã đang sở hữu, watchlist và cảnh báo đã bật.",
    )
    return source


def cleanup_recommendations(source: str) -> str:
    source = source.replace("Tín hiệu hành động đã được StockRadar phát hành.", "Tín hiệu đã phát hành.")
    return source


def process(output: Path, route: str) -> None:
    page = output / route / "index.html"
    source = read(page)
    transform = {
        "signup": cleanup_signup,
        "dang-ky": cleanup_plans,
        "thanh-toan": cleanup_checkout,
        "hieu-qua": cleanup_performance,
        "tai-khoan": cleanup_account,
        "hom-nay": cleanup_today,
        "khuyen-nghi": cleanup_recommendations,
    }[route]
    page.write_text(transform(source), encoding="utf-8")


def verify(output: Path) -> None:
    pages = {route: read(output / route / "index.html") for route in ROUTES}
    forbidden = {
        "signup": ("premium-email-onboarding-v1", "Để StockRadar canh mã thay bạn"),
        "dang-ky": ("production đạt chuẩn vận hành", "Gói 199K/30 ngày hiện được vận hành"),
        "thanh-toan": ("Tài khoản nhận tiền vẫn là VPBank", "Điều này giúp StockRadar đối soát"),
        "hieu-qua": ("Hãy nhìn dữ liệu thực tế trước khi quyết định trả phí", "KẾT QUẢ TRƯỚC, CÁCH ĐO SAU"),
        "tai-khoan": ("metadata vận hành", "cá nhân hóa sâu hơn"),
        "hom-nay": ("Bảng Hôm nay hiển thị theo trạng thái tài khoản đã xác định",),
        "khuyen-nghi": ("Tín hiệu hành động đã được StockRadar phát hành",),
    }
    for route, terms in forbidden.items():
        low = pages[route].lower()
        for term in terms:
            if term.lower() in low:
                raise RuntimeError(f"Residual explanatory copy survived on {route}: {term}")

    # Preserve conversion/auth/billing functionality using actual final-artifact hooks.
    required = {
        "signup": ("data-auth-signup-form", "data-signup-plan-name", "data-signup-submit-label"),
        "dang-ky": ("data-plan-free", "data-plan-premium", "data-plan-comparison"),
        "thanh-toan": ("data-checkout-confirm", "vpbank-qr-static.svg", "0934389822", "data-checkout-reference"),
        "hieu-qua": ("data-performance-summary",),
        "tai-khoan": ("data-product-email-preferences", "data-account-personalization", "data-account-watchlist-form"),
        "hom-nay": ("data-paid-dashboard",),
        "khuyen-nghi": ("data-recommendations", "data-recommendation-journal"),
    }
    for route, markers in required.items():
        source = pages[route]
        for marker in markers:
            if marker not in source:
                raise RuntimeError(f"Functional marker missing after cleanup: {route}: {marker}")
    print("Commercial cleanup v3: PASS (residual explanation removed; functional hooks preserved)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    for route in ROUTES:
        process(output, route)
    verify(output)


if __name__ == "__main__":
    main()
