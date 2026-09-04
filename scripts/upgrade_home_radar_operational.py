#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def patch_index(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    replacements = {
        "RADAR 30 · HOSE": "RADAR HOSE · QUÉT TOÀN THỊ TRƯỜNG",
        "<p>Bấm vào từng mã để mở trực tiếp trang phân tích Free/Premium.</p>": "<p>Danh sách chỉ được sinh từ snapshot hiện tại sau khi mã đi qua dữ liệu, thanh khoản, market/sector, rủi ro và Action Gate.</p>",
        "<div><span>Phương pháp quét</span><strong>Quét đa lớp HOSE</strong><small>4M · CANSLIM · Định giá · SEPA/VCP · VPA · Pocket Pivot.</small></div>": "<div><span>Hệ thống quét</span><strong>Full HOSE → Full-Scan Gate → Ranking</strong><small>Dữ liệu · 4M/Payback · CANSLIM · Định giá · Market/Sector · SEPA/VCP · VPA/RVOL · Catalyst · Risk.</small></div>",
        "<div><span>Quét trong phiên</span><strong>4 mốc/ngày</strong><small>10:30 · 11:15 · 13:30 · 14:15 · chỉ cảnh báo khi đạt chuẩn.</small></div>": "<div><span>Quét trong phiên</span><strong>4 mốc/ngày</strong><small>10:30 · 11:15 · 13:30 · 14:15 · RVOL/same-time volume · không đạt Action Gate thì không cảnh báo.</small></div>",
        "<a href=\"radar5/\"><span><strong>Radar 30</strong><span>30 mã · 10 ngành · 3 mã mỗi ngành</span></span><b>→</b></a>": "<a href=\"radar5/\"><span><strong>Radar HOSE</strong><span>Quét toàn sàn · xếp hạng theo snapshot · không đủ gate thì không vào danh sách</span></span><b>→</b></a>",
        "<div class=\"home-tier-feature\"><strong>Radar 30</strong><span>30 mã được chia cân bằng 10 ngành, 3 mã mỗi ngành.</span></div>": "<div class=\"home-tier-feature\"><strong>Radar HOSE</strong><span>Quét toàn bộ HOSE và chỉ đưa các mã đủ dữ liệu, thanh khoản, bối cảnh và chất lượng setup vào danh sách.</span></div>",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    start_marker = '<div class="home-radar-sector-list"'
    note_marker = '<div class="home-radar-note">'
    if start_marker in text and note_marker in text:
        start = text.index(start_marker)
        note_start = text.index(note_marker, start)
        note_end = text.index("</div>", note_start) + len("</div>")
        replacement = '''<div class="home-radar-sector-list" data-live-radar-home aria-label="Radar HOSE theo snapshot">
            <div class="home-radar-note"><strong>Radar động theo snapshot.</strong> Không có danh sách mã cố định. Dữ liệu public chỉ hiển thị sau khi production manifest, quyền dữ liệu và các quality gate đều đạt; nếu chưa đạt, hệ thống fail-closed thay vì dùng mã mẫu.</div>
          </div>'''
        text = text[:start] + replacement + text[note_end:]

    # Never leave fixed-list marketing language in the operational homepage.
    text = text.replace("Radar <strong>30 mã</strong>", "Radar <strong>theo snapshot</strong>")
    text = text.replace("Ngành <strong>10 × 3</strong>", "Ngành <strong>xếp hạng động</strong>")

    path.write_text(text, encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("root", nargs="?", default="website")
    args = p.parse_args()
    path = Path(args.root) / "index.html"
    if not path.exists():
        raise SystemExit(f"missing homepage: {path}")
    patch_index(path)


if __name__ == "__main__":
    main()
