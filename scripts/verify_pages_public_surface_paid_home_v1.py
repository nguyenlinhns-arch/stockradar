#!/usr/bin/env python3
"""Run the production public-surface verifier with the paid-intent homepage contract."""

from __future__ import annotations

import verify_pages_public_surface as base


ORIGINAL_REQUIRE = base.require_text
OLD_HOME_MARKERS = {
    "home-radar-sector-list",
    "home-tier-grid",
    "home-decision-v2",
    "Free và Premium có gì?",
    "Lý do chính",
    "Biên an toàn &amp; kỳ vọng",
    "Trạng thái giá",
    "Dòng tiền &amp; rủi ro",
    "Email & cảnh báo trong phiên",
    "4 mốc/ngày",
}
NEW_HOME_MARKERS = (
    "data-home-paid-intent-v1",
    "home-paid-intent-v1.css",
    "home-paid-intent-v1.js",
    "Đừng tự canh từng mã. Hãy để StockRadar theo dõi việc cần làm.",
    "KIỂM CHỨNG TRƯỚC KHI TRẢ TIỀN",
    "Có cả lãi và lỗ",
    "Không tính lệnh chưa kích hoạt",
    "199.000đ",
    "Theo dõi mã của tôi",
)


def paid_require_text(output, relative_path, expected, errors):
    if relative_path == "index.html":
        expected = tuple(marker for marker in expected if marker not in OLD_HOME_MARKERS) + NEW_HOME_MARKERS
    return ORIGINAL_REQUIRE(output, relative_path, expected, errors)


base.require_text = paid_require_text
base.main()
