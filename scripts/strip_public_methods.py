#!/usr/bin/env python3
"""Remove internal analysis-method jargon from the final StockRadar Pages artifact."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


BANNED_PUBLIC_TERMS = (
    "4M",
    "CANSLIM",
    "SEPA",
    "VCP",
    "VPA",
    "RVOL",
    "Pocket Pivot",
    "Early Breakout",
    "Confirmed Breakout",
    "Payback",
    "Wyckoff",
    "Minervini",
    "O’Neil",
    "O'Neil",
    "Phil Town",
    "Bear/Base/Bull",
    "Bear · Base · Bull",
    "Bear / Base / Bull",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def rewrite(source: str) -> str:
    replacements = (
        (
            'content="Tra cứu và phân tích cổ phiếu HOSE theo 4M, CANSLIM, định giá, SEPA/VCP, VPA và kế hoạch giao dịch."',
            'content="Tra cứu cổ phiếu HOSE theo bốn khung đầu tư, trạng thái hành động và quản trị rủi ro."',
        ),
        ('<title>Phân tích cổ phiếu — StockRadar</title>', '<title>Tra cứu cổ phiếu — StockRadar</title>'),
        ('<span>Phân tích cổ phiếu</span>', '<span>Tra cứu cổ phiếu</span>'),
        ('<h1>Phân tích cổ phiếu HOSE</h1>', '<h1>Tra cứu cổ phiếu HOSE</h1>'),
        ('<p>4M · CANSLIM · Định giá · SEPA/VCP · VPA · Kế hoạch giao dịch.</p>', '<p>Xem trạng thái theo bốn khung đầu tư, vùng hành động và rủi ro cần theo dõi.</p>'),
        ('>Phân tích</button>', '>Xem trạng thái</button>'),
        ('data-readiness="PHÂN TÍCH STOCKRADAR"', 'data-readiness="TRẠNG THÁI STOCKRADAR"'),
        ('StockRadar kết hợp phân tích doanh nghiệp, định giá, kỹ thuật, dòng tiền và quản trị rủi ro.', 'StockRadar tổng hợp dữ liệu thành trạng thái, vùng hành động và quản trị rủi ro.'),
        ('Setup · Vùng giá · Dòng tiền · Market Direction', 'Trạng thái · Vùng giá · Dòng tiền · Thị trường'),
        ('PHƯƠNG PHÁP ĐO NHẤT QUÁN', 'QUY TẮC ĐO NHẤT QUÁN'),
        ('MẪU PHƯƠNG PHÁP', 'QUY TẮC'),
        ('Phương pháp StockRadar', 'Cách dùng StockRadar'),
        ('Phương pháp quét', 'Cách StockRadar rà soát'),
        ('setup đạt chuẩn', 'điều kiện hành động đạt chuẩn'),
        ('Setup đạt chuẩn', 'Điều kiện hành động đạt chuẩn'),
        ('setup và dữ liệu cùng đạt chuẩn', 'điều kiện hành động và dữ liệu cùng đạt chuẩn'),
        ('Setup và dữ liệu cùng đạt chuẩn', 'Điều kiện hành động và dữ liệu cùng đạt chuẩn'),
        ('một setup đạt chuẩn hành động', 'điều kiện hành động đạt chuẩn'),
        ('Không có setup đạt chuẩn', 'Không có điều kiện hành động đạt chuẩn'),
        ('Pocket Pivot · Early Breakout · Confirmed Breakout · Retest', 'Mua · chờ · theo dõi · bỏ qua'),
        ('Pocket Pivot · Early Breakout · Confirmed Breakout', 'Mua · chờ · theo dõi'),
        ('Pocket Pivot · Breakout · Retest', 'Mua · chờ · theo dõi · bỏ qua'),
        ('Đạt vùng mua · Chờ mua · Theo dõi · Bỏ qua.', 'Mua · chờ · theo dõi · bỏ qua.'),
        ('SEPA · VCP · VPA · RVOL', 'TRẠNG THÁI HÀNH ĐỘNG'),
        ('4M · SEPA · VPA', 'TRẠNG THÁI · DÒNG TIỀN · RỦI RO'),
    )
    for before, after in replacements:
        source = source.replace(before, after)

    # Generated ticker pages are created before the final production UX pass.
    source = re.sub(
        r'<title>([A-Z0-9]{3}) — Phân tích Free &amp; Premium \| StockRadar</title>',
        r'<title>\1 — Tra cứu &amp; quyết định | StockRadar</title>',
        source,
    )
    source = re.sub(
        r'Phân tích ([A-Z0-9]{3}) \(([^<"]+)\) trên StockRadar: bản Free công khai và cấu trúc Premium chuyên sâu\.',
        r'Tra cứu \1 (\2) trên StockRadar: trạng thái Free công khai và lớp quyết định Premium.',
        source,
    )

    # Old knowledge links are not published in production; route users to the live lookup instead.
    source = re.sub(
        r'href=["\'][^"\']*kien-thuc/(?:canslim-sepa|vpa|4m|pocket-pivot)/["\']',
        'href="kiem-tra-co-phieu/"',
        source,
        flags=re.IGNORECASE,
    )
    return source


def main() -> None:
    output = parse_args().output.resolve()
    if not output.is_dir():
        raise RuntimeError(f"Pages output does not exist: {output}")

    pages = sorted(output.rglob("*.html"))
    for page in pages:
        source = rewrite(page.read_text(encoding="utf-8"))
        page.write_text(source, encoding="utf-8")

    leaks: list[str] = []
    for page in pages:
        source = page.read_text(encoding="utf-8")
        for term in BANNED_PUBLIC_TERMS:
            if term.casefold() in source.casefold():
                leaks.append(f"{page.relative_to(output)}: {term}")

    if leaks:
        raise RuntimeError("Public method jargon remains:\n- " + "\n- ".join(leaks))

    print(f"Public method-jargon scrub: PASS ({len(pages)} HTML pages)")


if __name__ == "__main__":
    main()
