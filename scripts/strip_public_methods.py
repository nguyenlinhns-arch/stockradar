#!/usr/bin/env python3
"""Remove internal method jargon and analysis-language from the final StockRadar Pages artifact."""

from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path


BANNED_PUBLIC_TERMS = (
    "phân tích",
    "phương pháp",
    "setup",
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
    "Ichimoku",
    "Bollinger",
    "Trendline",
    "Bear/Base/Bull",
    "Bear · Base · Bull",
    "Bear / Base / Bull",
)
RUNTIME_GUARD = "decision-copy-guard-v1.js"
RUNTIME_MARKER = "data-decision-copy-guard-v1"


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
        ('Nhìn trạng thái, không cần học phương pháp.', 'Chỉ cần nhìn trạng thái và hành động.'),
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
        ('phân tích chuyên sâu', 'chi tiết quyết định'),
        ('Phân tích chuyên sâu', 'Chi tiết quyết định'),
        ('phân tích sâu hơn', 'quyết định chi tiết hơn'),
        ('Phân tích sâu hơn', 'Quyết định chi tiết hơn'),
        ('phân tích sâu', 'quyết định chi tiết'),
        ('Phân tích sâu', 'Quyết định chi tiết'),
        ('phân tích công khai', 'dữ liệu công khai'),
        ('Phân tích công khai', 'Dữ liệu công khai'),
        ('phân tích cơ bản', 'bối cảnh'),
        ('Phân tích cơ bản', 'Bối cảnh'),
        ('phân tích kỹ thuật', 'trạng thái giá'),
        ('Phân tích kỹ thuật', 'Trạng thái giá'),
        ('phân tích doanh nghiệp', 'dữ liệu doanh nghiệp'),
        ('Phân tích doanh nghiệp', 'Dữ liệu doanh nghiệp'),
        ('nhu cầu phân tích', 'nhu cầu sử dụng'),
        ('Nhu cầu phân tích', 'Nhu cầu sử dụng'),
        ('trang phân tích', 'trang trạng thái'),
        ('Trang phân tích', 'Trang trạng thái'),
        ('phân tích Free/Premium', 'trạng thái Free/Premium'),
        ('Phân tích Free/Premium', 'Trạng thái Free/Premium'),
        ('phân tích Free & Premium', 'trạng thái Free & Premium'),
        ('Phân tích Free & Premium', 'Trạng thái Free & Premium'),
        ('phân tích đa khung', 'trạng thái đa khung'),
        ('Phân tích đa khung', 'Trạng thái đa khung'),
        ('phân tích cổ phiếu', 'tra cứu cổ phiếu'),
        ('Phân tích cổ phiếu', 'Tra cứu cổ phiếu'),
    )
    for before, after in replacements:
        source = source.replace(before, after)

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

    source = re.sub(
        r'href=["\'](?:\.\./)*phan-tich/(?:[^"\']*)?["\']',
        'href="kiem-tra-co-phieu/"',
        source,
        flags=re.IGNORECASE,
    )
    source = re.sub(
        r'href=["\'][^"\']*kien-thuc/(?:canslim-sepa|vpa|4m|pocket-pivot)/["\']',
        'href="kiem-tra-co-phieu/"',
        source,
        flags=re.IGNORECASE,
    )

    source = source.replace("PHÂN TÍCH", "TRẠNG THÁI")
    source = source.replace("Phân tích", "Tra cứu")
    source = source.replace("phân tích", "tra cứu")
    source = source.replace("PHƯƠNG PHÁP", "QUY TẮC")
    source = source.replace("Phương pháp", "Cách dùng")
    source = source.replace("phương pháp", "cách dùng")
    source = source.replace("SETUP", "TRẠNG THÁI")
    source = source.replace("Setup", "Trạng thái")
    source = source.replace("setup", "trạng thái")
    return source


def guard_src(source: str, page: Path, output: Path) -> str:
    if re.search(r'<base\s+[^>]*href=["\'][^"\']+["\']', source, flags=re.IGNORECASE):
        return f"assets/{RUNTIME_GUARD}"
    target = output / "assets" / RUNTIME_GUARD
    return os.path.relpath(target, page.parent).replace(os.sep, "/")


def inject_runtime_guard(source: str, page: Path, output: Path) -> str:
    if RUNTIME_MARKER in source:
        return source
    if "</head>" not in source:
        raise RuntimeError(f"Cannot inject decision copy guard: {page.relative_to(output)} has no </head>")
    src = guard_src(source, page, output)
    tag = f'<script src="{src}?v=20260904-decision1" defer {RUNTIME_MARKER}></script>\n'
    return source.replace("</head>", tag + "</head>", 1)


def main() -> None:
    output = parse_args().output.resolve()
    if not output.is_dir():
        raise RuntimeError(f"Pages output does not exist: {output}")

    guard_asset = output / "assets" / RUNTIME_GUARD
    if not guard_asset.is_file():
        raise RuntimeError(f"Missing decision-first runtime guard: {RUNTIME_GUARD}")

    legacy_analysis = output / "phan-tich"
    if legacy_analysis.exists():
        shutil.rmtree(legacy_analysis)

    pages = sorted(output.rglob("*.html"))
    for page in pages:
        source = rewrite(page.read_text(encoding="utf-8"))
        source = inject_runtime_guard(source, page, output)
        page.write_text(source, encoding="utf-8")

    leaks: list[str] = []
    for page in pages:
        source = page.read_text(encoding="utf-8")
        for term in BANNED_PUBLIC_TERMS:
            if term.casefold() in source.casefold():
                leaks.append(f"{page.relative_to(output)}: {term}")
        if RUNTIME_MARKER not in source:
            leaks.append(f"{page.relative_to(output)}: missing runtime decision-copy guard")

    if leaks:
        raise RuntimeError("Public decision-first surface still contains banned analysis language:\n- " + "\n- ".join(leaks))

    if legacy_analysis.exists():
        raise RuntimeError("Legacy /phan-tich/ route remains in production artifact")

    print(f"Public decision-first scrub: PASS ({len(pages)} HTML pages; /phan-tich/ retired; runtime guard injected)")


if __name__ == "__main__":
    main()
