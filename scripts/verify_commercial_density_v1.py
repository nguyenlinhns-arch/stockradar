#!/usr/bin/env python3
"""Fail the Pages build if buyer-facing pages become verbose or instructional again."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

BUDGETS = {
    "": 1700,
    "radar5": 600,
    "kiem-tra-co-phieu": 550,
    "khuyen-nghi": 800,
    "nganh": 350,
    "hieu-qua": 500,
    "dang-ky": 1200,
    "signup": 900,
    "dang-nhap": 450,
    "thanh-toan": 1700,
    "co-phieu": 1000,
    "tai-khoan": 2850,
    "hom-nay": 850,
    "breakout": 550,
    "risk": 550,
    "track-record": 550,
    "thay-doi-hom-nay": 550,
    "nhan-ban-tin": 400,
}

BANNED_VISIBLE = (
    "data gate",
    "provider secret",
    "kết quả trước, cách đo sau",
    "hãy nhìn dữ liệu thực tế trước khi quyết định trả phí",
    "để stockradar canh mã thay bạn",
    "production đạt chuẩn vận hành",
    "gói 199k/30 ngày hiện được vận hành",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def page_path(output: Path, route: str) -> Path:
    return output / "index.html" if route == "" else output / route / "index.html"


def visible_main(source: str) -> str:
    match = re.search(r'<main\b[^>]*>(.*?)</main>', source, flags=re.I | re.S)
    if not match:
        raise RuntimeError("Missing <main>")
    text = match.group(1)
    # Closed disclosure panels expose their summary in the initial page, not their body.
    def disclosure(match):
        if re.search(r'(?:^|\s)open(?:\s|=|$)', match.group(1), flags=re.I):
            return match.group(2)
        summary = re.search(r'<summary\b[^>]*>.*?</summary>', match.group(2), flags=re.I | re.S)
        return summary.group(0) if summary else ''
    text = re.sub(r'<details\b([^>]*)>(.*?)</details>', disclosure, text, flags=re.I | re.S)
    # Template/script/style/noscript content is not buyer-visible and must not inflate copy budgets.
    text = re.sub(
        r'<(?:script|style|noscript|template)\b.*?</(?:script|style|noscript|template)>',
        ' ',
        text,
        flags=re.I | re.S,
    )
    text = re.sub(r'<[^>]+>', ' ', text)
    return ' '.join(html.unescape(text).split())


def main() -> None:
    args = parse_args()
    output = args.output.resolve()
    checked = 0
    for route, budget in BUDGETS.items():
        path = page_path(output, route)
        if not path.is_file():
            raise RuntimeError(f"Commercial density route missing: {path}")
        source = path.read_text(encoding="utf-8")
        visible = visible_main(source)
        if len(visible) > budget:
            raise RuntimeError(f"Commercial page too verbose: {route or '/'}: {len(visible)} > {budget} chars")
        h1_count = len(re.findall(r'<h1\b', source, flags=re.I))
        if h1_count != 1:
            raise RuntimeError(f"Expected one h1 on {route or '/'}; found {h1_count}")
        low = visible.lower()
        for term in BANNED_VISIBLE:
            if term in low:
                raise RuntimeError(f"Explanatory/internal copy visible on {route or '/'}: {term}")
        checked += 1
    print(f"Commercial density QA: PASS ({checked} routes within copy budgets)")


if __name__ == "__main__":
    main()
