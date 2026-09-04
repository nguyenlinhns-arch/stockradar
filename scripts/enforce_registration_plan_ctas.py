#!/usr/bin/env python3
"""Lock the final StockRadar registration plan cards after all Pages transforms.

Commercial rule:
- Free is always available while account auth is configured.
- Premium benefits may be shown, but new paid activation is fail-closed unless
  STOCKRADAR_CHECKOUT_READY is explicitly enabled.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


STYLE_MARKER = "data-pricing-professional-v2"
STYLE_LINK = (
    '<link rel="stylesheet" href="assets/pricing-professional-v2.css?v=20260904-pricing2" '
    f'{STYLE_MARKER}>'
)


def checkout_ready() -> bool:
    return os.environ.get("STOCKRADAR_CHECKOUT_READY", "").strip().lower() in {"1", "true", "yes", "on"}


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
        <p>Bắt đầu miễn phí. Premium chỉ mở thanh toán khi dữ liệu quyết định và hệ thống cảnh báo đã đạt chuẩn production.</p>
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


def premium_card() -> str:
    ready = checkout_ready()
    ribbon = 'ĐẦY ĐỦ TÍNH NĂNG' if ready else 'TẠM DỪNG KÍCH HOẠT MỚI'
    kicker = '199K / 30 NGÀY' if ready else 'PREMIUM · CHỜ PRODUCTION GATE'
    note = (
        'Chu kỳ Premium là 30 ngày, không tự gia hạn. Tạo và xác minh tài khoản trước khi sang bước thanh toán.'
        if ready else
        'StockRadar đang tạm dừng nhận thanh toán Premium mới cho tới khi Decision Feed, AI và email Action Alert hoàn tất kiểm thử end-to-end. Bạn vẫn có thể tạo tài khoản để ghi nhận nhu cầu Premium.'
    )
    cta = 'Đăng ký' if ready else 'Đăng ký nhận thông báo'
    return f'''<article class="plan-card plan-card-premium conversion-plan-card" data-plan-premium id="premium" data-checkout-ready="{'true' if ready else 'false'}">
            <span class="plan-ribbon" aria-label="{ribbon}"><span aria-hidden="true">★</span> {ribbon}</span>
            <span class="plan-kicker">{kicker}</span>
            <h2>StockRadar Premium</h2>
            <div class="plan-price"><strong>199.000đ</strong><span>/ 30 ngày</span></div>
            <p class="plan-summary">Dành cho người muốn có lớp quyết định đầy đủ, vùng hành động và cảnh báo khi trạng thái thay đổi.</p>
            <ul class="plan-feature-list">
              <li><strong>StockRadar AI:</strong> không giới hạn câu hỏi theo quyền gói Premium</li>
              <li><strong>Mua mới:</strong> MUA / CHỜ theo từng khung</li>
              <li><strong>Đang nắm giữ:</strong> GIỮ / TĂNG / GIẢM / BÁN</li>
              <li><strong>Vùng hành động:</strong> Buy Zone · tỷ trọng · Stop · Target · Risk/Reward</li>
              <li><strong>Báo cáo 09:00</strong> và cảnh báo thay đổi tại 10:30 · 11:15 · 13:30 · 14:15</li>
              <li><strong>My StockRadar:</strong> watchlist mở rộng và ưu tiên mã người dùng quan tâm</li>
            </ul>
            <div class="plan-info-box plan-info-box-premium">{note}</div>
            <a class="button button-primary" href="signup/?plan=premium" data-registration-plan="premium" data-premium-conversion-cta data-conversion-action="plans_premium">{cta}</a>
          </article>'''


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
              <li>StockRadar AI Free: 10 câu/ngày sau khi đăng nhập</li>
              <li>Tra cứu cổ phiếu HOSE và xem dữ liệu công khai</li>
              <li>Radar và góc nhìn theo ngành</li>
              <li>Danh sách theo dõi cá nhân cơ bản</li>
              <li>Email hệ thống cần thiết cho xác minh và bảo mật tài khoản</li>
            </ul>
            <div class="plan-info-box">Free không nhận Daily 09:00 hoặc cảnh báo điểm mua/bán trong phiên.</div>
            <a class="button button-secondary" href="signup/?plan=free" data-registration-plan="free">Đăng ký</a>
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
        premium_card(),
        "Premium",
    )
    source = _ensure_final_style(source)

    required = (
        'data-plan-free',
        'data-plan-premium',
        'href="signup/?plan=free" data-registration-plan="free">Đăng ký</a>',
        'href="signup/?plan=premium" data-registration-plan="premium"',
        'GÓI DỊCH VỤ',
        '199.000đ',
        '10 câu/ngày',
        'Free không nhận Daily 09:00',
        'plan-info-box',
        STYLE_MARKER,
    )
    for marker in required:
        if marker not in source:
            raise RuntimeError(f"Registration plan contract missing: {marker}")

    if checkout_ready():
        if '>Đăng ký</a>' not in source:
            raise RuntimeError("Premium checkout-open CTA missing")
    else:
        for marker in ('TẠM DỪNG KÍCH HOẠT MỚI', 'Đăng ký nhận thông báo', 'data-checkout-ready="false"'):
            if marker not in source:
                raise RuntimeError(f"Premium fail-closed plan marker missing: {marker}")

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
    print(f"Locked registration plans (checkout_ready={checkout_ready()}): {page}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
