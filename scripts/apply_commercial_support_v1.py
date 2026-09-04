#!/usr/bin/env python3
"""Compact secondary StockRadar routes that remain useful but are not primary navigation."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROUTES = ("breakout", "risk", "track-record", "thay-doi-hom-nay", "nhan-ban-tin")
STYLE = "commercial-v1.css"
SUPPORT_STYLE = "commercial-support-v1.css"
RUNTIME = "commercial-v1.js"
MARKER = "data-commercial-support-v1"


def read(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"Missing support route: {path}")
    return path.read_text(encoding="utf-8")


def inject_assets(source: str) -> str:
    if MARKER in source:
        return source
    if "</head>" not in source:
        raise RuntimeError("Support route has no closing head")
    tags = (
        f'<link rel="stylesheet" href="assets/{STYLE}?v=20260904-commercial3">\n'
        f'<link rel="stylesheet" href="assets/{SUPPORT_STYLE}?v=20260904-commercial3" {MARKER}>\n'
        f'<script src="assets/{RUNTIME}?v=20260904-commercial3" defer></script>'
    )
    return source.replace("</head>", tags + "\n</head>", 1)


def nav(source: str) -> str:
    replacement = '<nav class="nav-links" id="site-menu" aria-label="Điều hướng chính" data-nav-menu><a href="./#stockradar-ai">AI</a><a href="hom-nay/">Hôm nay</a><a href="radar5/">Radar</a><a href="khuyen-nghi/">Khuyến nghị</a><a href="hieu-qua/">Hiệu quả</a></nav>'
    source, count = re.subn(r'<nav\b[^>]*data-nav-menu[^>]*>.*?</nav>', replacement, source, count=1, flags=re.I | re.S)
    if count != 1:
        raise RuntimeError("Support route nav not found")
    return source


def footer(source: str) -> str:
    replacement = '<footer class="site-footer commercial-footer"><div class="container"><div class="footer-grid"><strong>STOCKRADAR.VN</strong><div class="footer-links"><a href="dieu-khoan/">Điều khoản</a><a href="quyen-rieng-tu/">Quyền riêng tư</a></div></div><p class="disclaimer">Công cụ hỗ trợ quyết định đầu tư. Không cam kết lợi nhuận, không tự đặt lệnh.</p></div></footer>'
    source, count = re.subn(r'<footer\b[^>]*class=["\'][^"\']*\bsite-footer\b[^"\']*["\'][^>]*>.*?</footer>', replacement, source, count=1, flags=re.I | re.S)
    if count != 1:
        raise RuntimeError("Support route footer not found")
    return source


def compact_breakout(source: str) -> str:
    source = source.replace("Điểm mua StockRadar", "Điểm mua")
    source = source.replace("TRẠNG THÁI HÀNH ĐỘNG", "ĐIỂM MUA")
    return source


def compact_risk(source: str) -> str:
    source = source.replace("<h1>Quản trị rủi ro</h1>", "<h1>Cảnh báo rủi ro</h1>")
    source = source.replace("Stop-loss · Hạ tỷ trọng · Cắt lỗ · Risk/Reward.", "Hạ tỷ trọng · Cắt lỗ · Rủi ro.")
    source = source.replace("4 MỐC QUÉT TRONG PHIÊN", "TRONG PHIÊN")
    return source


def compact_track_record(source: str) -> str:
    source = source.replace("<h1>Lịch sử StockRadar</h1>", "<h1>Lịch sử tín hiệu</h1>")
    source = source.replace("Dấu thời gian · Entry · Target/Stop · Vòng đời khuyến nghị.", "Thời gian · Giá vào · Target/Stop · Trạng thái.")
    source = source.replace("NHẬT KÝ APPEND-ONLY", "LỊCH SỬ")
    return source


def compact_today_changes(source: str) -> str:
    source = source.replace("Setup · Vùng giá · Dòng tiền · Market Direction.", "Vùng giá · Dòng tiền · Trạng thái.")
    source = source.replace("4 MỐC QUÉT TRONG PHIÊN", "TRONG PHIÊN")
    return source


def compact_newsletter(source: str) -> str:
    main = '''<main id="content" class="lead-shell commercial-email-lead">
      <section class="lead-hero"><div class="lead-wrap commercial-lead-wrap">
        <article class="lead-card" aria-labelledby="lead-title">
          <header class="lead-card-head"><span>PREMIUM</span><h1 id="lead-title">Email StockRadar</h1><p>Daily 09:00 + Action Alert theo watchlist.</p></header>
          <form class="lead-form email-interest-form" data-email-interest-form data-next-href="signup/?plan=premium" data-next-label="Tiếp tục đăng ký Premium" novalidate>
            <div class="lead-field"><label for="lead-email">Email</label><input id="lead-email" name="email" type="email" inputmode="email" autocomplete="email" maxlength="160" required placeholder="email@example.com"></div>
            <label class="lead-check"><input name="daily_brief" type="checkbox"><span>Daily 09:00 Premium</span></label>
            <label class="lead-check"><input name="event_alerts" type="checkbox"><span>Action Alert khi trạng thái thay đổi</span></label>
            <label class="lead-check"><input name="privacy" type="checkbox" required><span>Tôi đồng ý <a href="quyen-rieng-tu/">Chính sách quyền riêng tư</a>.</span></label>
            <div class="lead-honeypot" aria-hidden="true"><label for="lead-company">Công ty</label><input id="lead-company" name="company" type="text" autocomplete="off" tabindex="-1"></div>
            <button class="lead-submit" type="submit">Tiếp tục Premium</button>
            <p class="email-interest-message" data-email-interest-message aria-live="polite">Không tự thu phí · Không tự gia hạn.</p>
          </form>
          <div class="commercial-lead-actions"><a href="dang-ky/?plan=premium">Xem gói Premium</a><a href="dang-nhap/">Đăng nhập</a></div>
        </article>
      </div></section>
    </main>'''
    source, count = re.subn(r'<main\b[^>]*>.*?</main>', main, source, count=1, flags=re.I | re.S)
    if count != 1:
        raise RuntimeError("Newsletter main not found")
    return source


def process(output: Path, route: str) -> None:
    page = output / route / "index.html"
    source = footer(nav(inject_assets(read(page))))
    transform = {
        "breakout": compact_breakout,
        "risk": compact_risk,
        "track-record": compact_track_record,
        "thay-doi-hom-nay": compact_today_changes,
        "nhan-ban-tin": compact_newsletter,
    }[route]
    page.write_text(transform(source), encoding="utf-8")


def verify(output: Path) -> None:
    pages = {route: read(output / route / "index.html") for route in ROUTES}
    for route, source in pages.items():
        if MARKER not in source:
            raise RuntimeError(f"Commercial support bundle missing: {route}")
        if "Tra cứu mã</a>" in source or "Gói dịch vụ</a>" in source:
            raise RuntimeError(f"Legacy nav survived: {route}")
    newsletter = pages["nhan-ban-tin"]
    for marker in ("data-email-interest-form", "daily_brief", "event_alerts", "privacy"):
        if marker not in newsletter:
            raise RuntimeError(f"Newsletter functional marker missing: {marker}")
    for forbidden in ("GIÁ TRỊ PREMIUM", "lead-value-grid", "lead-upgrade", "không cần tự canh từng mã"):
        if forbidden.lower() in newsletter.lower():
            raise RuntimeError(f"Verbose newsletter copy survived: {forbidden}")
    print("Commercial support routes: PASS (secondary routes compact and consistent)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    for asset in (STYLE, SUPPORT_STYLE, RUNTIME):
        if not (output / "assets" / asset).is_file():
            raise RuntimeError(f"Missing support asset: {asset}")
    for route in ROUTES:
        process(output, route)
    verify(output)


if __name__ == "__main__":
    main()
