#!/usr/bin/env python3
"""Run conversion v3 verification with AI-first homepage and Premium-email contracts."""

from __future__ import annotations

import verify_conversion_v3 as base


ORIGINAL_REQUIRE = base.require


def paid_require(source: str, *markers: str, label: str) -> None:
    if label == "homepage conversion":
        if "data-stockradar-ai-center" in source:
            markers = (
                "data-stockradar-ai-center",
                "Hỏi một mã cổ phiếu",
                "3 câu/ngày",
                "10 câu/ngày",
                "Hỏi không giới hạn",
                "signup/?plan=free",
                "dang-ky/?plan=premium",
            )
        else:
            markers = tuple(marker for marker in markers if marker != "home-decision-v2") + (
                "data-home-paid-intent-v1",
                "KIỂM CHỨNG TRƯỚC KHI TRẢ TIỀN",
                "199.000đ",
                "Theo dõi mã của tôi",
            )
    elif label == "signup conversion":
        markers = tuple(
            "Tùy chọn email Premium" if marker == "Tùy chọn nhận email" else marker
            for marker in markers
        ) + (
            "Trial/Paid",
            "Không mục email nội dung nào được chọn sẵn",
        )
    return ORIGINAL_REQUIRE(source, *markers, label=label)


base.require = paid_require
base.main()
