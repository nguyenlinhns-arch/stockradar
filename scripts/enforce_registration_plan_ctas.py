#!/usr/bin/env python3
"""Lock the final StockRadar registration plan cards after all Pages transforms.

Product + visual contract:
- two visible registration choices: Miễn phí and 199K/tháng;
- each choice has its own CTA labelled exactly "Đăng ký";
- Premium goes through account creation/verification before payment;
- final production artifact uses the dedicated professional pricing stylesheet loaded last.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


STYLE_MARKER = "data-pricing-professional-v2"
STYLE_LINK = (
    '<link rel="stylesheet" href="assets/pricing-professional-v2.css?v=20260904-pricing2" '
    f'{STYLE_MARKER}>'
)


def _replace_card(source: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, source, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"Could not locate {label} plan card")
    return updated


def _replace_hero(source: str) -> str:
    hero = '''<section class="plans-hero">
      <div class="plans-hero-inner">
        <span class="panel-label">GÓI DỊCH VỤ</span>
        <h1>Chọn gói phù hợp với nhu cầu của bạn</h1>
        <p>Bắt đầu miễn phí, nâng cấp dễ dàng khi bạn sẵn sàng.</p>
      </div>
    </section>'''
    updated, count = re.subn(
        r'<section class="plans-hero">.*?</section>',
        hero,
        source,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise RuntimeError("Could not locate plans hero")
    return updated


def _ensure_final_style(source: str) -> str:
    if STYLE_MARKER in source:
        return source
    if "</head>" not in source:
        raise RuntimeError("Registration page has no closing head tag")
    return source.replace("</head>", f"  {STYLE_LINK}\n</head>", 1)


def enforce(output: Path) -> Path:
    page = output / "dang-ky" / "index.html"
    if not page.exists():
        raise FileNotFoundError(page)

    source = page.read_text(encoding="utf-8")
    source = _replace_hero(source)

    free_card = '''<article class="plan-card" data-plan-free>
            <span class="plan-kicker">MIỄN PHÍ</span>
            <h2>StockRadar Free</h2>
            <div class="plan-price"><strong>0đ</strong><span>/ tháng</span></div>
            <p class="plan-summary">Tra cứu và trải nghiệm StockRadar miễn phí trước khi nâng cấp.</p>
            <ul class="plan-feature-list">
              <li>Tra cứu cổ phiếu HOSE và xem dữ liệu công khai</li>
              <li>Radar và góc nhìn theo ngành</li>
              <li>Danh sách theo dõi cá nhân cơ bản</li>
              <li>StockRadar AI Free theo giới hạn của tài khoản</li>
              <li>Email hệ thống cần thiết cho xác minh và bảo mật tài khoản</li>
            </ul>
            <div class="plan-info-box">Free không nhận báo cáo 09:00 hoặc cảnh báo điểm mua/bán trong phiên.</div>
            <a class="button button-secondary" href="signup/?plan=free" data-registration-plan="free">Đăng ký</a>
          </article>'''

    premium_card = '''<article class="plan-card plan-card-premium conversion-plan-card" data-plan-premium id="premium">
            <span class="plan-ribbon" aria-label="ĐẦY ĐỦ TÍNH NĂNG"><span aria-hidden="true">★</span> Phổ biến</span>
            <span class="plan-kicker">199K / THÁNG</span>
            <h2>StockRadar Premium</h2>
            <div class="plan-price"><strong>199.000đ</strong><span>/ tháng</span></div>
            <p class="plan-summary">Dành cho người muốn có lớp quyết định đầy đủ, vùng hành động và cảnh báo khi trạng thái thay đổi.</p>
            <ul class="plan-feature-list">
              <li><strong>Mua mới:</strong> MUA / CHỜ theo từng khung</li>
              <li><strong>Đang nắm giữ:</strong> GIỮ / TĂNG / GIẢM / BÁN</li>
              <li><strong>Vùng hành động:</strong> Vùng mua · tỷ trọng · Stop · Target · Risk/Reward</li>
              <li><strong>Báo cáo 09:00</strong> và cảnh báo thay đổi tại 10:30 · 11:15 · 13:30 · 14:15</li>
              <li><strong>My StockRadar:</strong> watchlist mở rộng và ưu tiên mã người dùng quan tâm</li>
              <li><strong>StockRadar AI:</strong> không giới hạn câu hỏi theo quyền gói Premium</li>
            </ul>
            <div class="plan-info-box plan-info-box-premium">Chu kỳ Premium hiện tại là 30 ngày, không tự gia hạn. Tạo và xác minh tài khoản trước khi sang bước thanh toán.</div>
            <a class="button button-primary" href="signup/?plan=premium" data-registration-plan="premium" data-premium-conversion-cta data-conversion-action="plans_premium">Đăng ký</a>
          </article>'''

    source = _replace_card(
        source,
        r'<article class="plan-card" data-plan-free>.*?</article>',
        free_card,
        "Free",
    )
    source = _replace_card(
        source,
        r'<article class="plan-card plan-card-premium[^\"]*"[^>]*data-plan-premium[^>]*>.*?</article>',
        premium_card,
        "Premium",
    )
    source = _ensure_final_style(source)

    required = (
        'data-plan-free',
        'data-plan-premium',
        'href="signup/?plan=free" data-registration-plan="free">Đăng ký</a>',
        'href="signup/?plan=premium" data-registration-plan="premium"',
        '>Đăng ký</a>',
        'GÓI DỊCH VỤ',
        'Chọn gói phù hợp với nhu cầu của bạn',
        '199K / THÁNG',
        '199.000đ',
        'plan-info-box',
        STYLE_MARKER,
    )
    for marker in required:
        if marker not in source:
            raise RuntimeError(f"Registration plan contract missing: {marker}")
    if "Thanh toán / Nâng Premium" in source or ">Tạo tài khoản Premium</a>" in source:
        raise RuntimeError("Legacy Premium CTA leaked into final registration page")
    if source.count('data-registration-plan=') != 2:
        raise RuntimeError("Final registration page must contain exactly two plan registration CTAs")

    page.write_text(source, encoding="utf-8")
    return page


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    page = enforce(args.output)
    print(f"Locked professional registration plans: {page}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
