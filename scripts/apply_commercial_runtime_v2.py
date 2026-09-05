#!/usr/bin/env python3
"""Stabilize commercial runtime copy and shared chrome on conversion-critical routes."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROUTES = ("co-phieu", "signup", "dang-nhap", "thanh-toan")
SCRIPT_NAME = "commercial-v2.js"
SCRIPT_MARKER = "data-commercial-runtime-v2"


def read(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"Missing commercial runtime target: {path}")
    return path.read_text(encoding="utf-8")


def normalize_nav(source: str) -> str:
    nav = '<nav class="nav-links" id="site-menu" aria-label="Điều hướng chính" data-nav-menu><a href="./#stockradar-ai">AI</a><a href="hom-nay/">Hôm nay</a><a href="radar5/">Radar</a><a href="khuyen-nghi/">Khuyến nghị</a><a href="hieu-qua/">Hiệu quả</a></nav>'
    source, count = re.subn(r'<nav\b[^>]*data-nav-menu[^>]*>.*?</nav>', nav, source, count=1, flags=re.I | re.S)
    if count != 1:
        raise RuntimeError("Commercial runtime could not normalize navigation")
    return source


def normalize_footer(source: str) -> str:
    footer = '<footer class="site-footer commercial-footer"><div class="container"><div class="footer-grid"><strong>STOCKRADAR.VN</strong><div class="footer-links"><a href="dieu-khoan/">Điều khoản</a><a href="quyen-rieng-tu/">Quyền riêng tư</a></div></div><p class="disclaimer">Công cụ hỗ trợ quyết định đầu tư. Không cam kết lợi nhuận, không tự đặt lệnh.</p></div></footer>'
    source, count = re.subn(r'<footer\b[^>]*class=["\'][^"\']*\bsite-footer\b[^"\']*["\'][^>]*>.*?</footer>', footer, source, count=1, flags=re.I | re.S)
    if count != 1:
        raise RuntimeError("Commercial runtime could not normalize footer")
    return source


def inject_script(source: str) -> str:
    if SCRIPT_MARKER in source:
        return source
    if "</head>" not in source:
        raise RuntimeError("Commercial runtime target missing closing head")
    tag = f'<script src="assets/{SCRIPT_NAME}?v=20260905-email1" defer {SCRIPT_MARKER}></script>'
    return source.replace("</head>", tag + "\n</head>", 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if not (output / "assets" / SCRIPT_NAME).is_file():
        raise RuntimeError(f"Missing commercial runtime asset: {SCRIPT_NAME}")

    for route in ROUTES:
        page = output / route / "index.html"
        source = inject_script(normalize_footer(normalize_nav(read(page))))
        page.write_text(source, encoding="utf-8")

    for route in ROUTES:
        source = read(output / route / "index.html")
        if SCRIPT_MARKER not in source or SCRIPT_NAME not in source:
            raise RuntimeError(f"Commercial runtime not injected into {route}")
        if "Tra cứu mã</a><a href=\"khuyen-nghi/\"" in source:
            raise RuntimeError(f"Legacy navigation survived on {route}")

    print("Commercial runtime v2: PASS (shared chrome + compact dynamic copy)")


if __name__ == "__main__":
    main()
