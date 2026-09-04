#!/usr/bin/env python3
"""Lock the final StockRadar registration plan cards after all Pages transforms.

Product contract:
- two visible registration choices: Miễn phí and 199K/tháng;
- each choice has its own CTA labelled exactly "Đăng ký";
- Premium goes through account creation/verification before payment.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def _replace_card(source: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, source, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"Could not locate {label} plan card")
    return updated


def enforce(output: Path) -> Path:
    page = output / "dang-ky" / "index.html"
    if not page.exists():
        raise FileNotFoundError(page)

    source = page.read_text(encoding="utf-8")

    free_card = '''<article class="plan-card" data-plan-free>
            <span class="plan-kicker">MIỄN PHÍ</span>
            <h2>StockRadar Free — Miễn phí</h2>
            <div class="plan-price"><strong>0đ</strong><span>/ tháng</span></div>
            <p class="plan-summary">Tra cứu và trải nghiệm StockRadar miễn phí trước khi nâng cấp.</p>
            <ul class="plan-feature-list">
              <li>Tra cứu cổ phiếu HOSE và xem dữ liệu công khai.</li>
              <li>Radar và góc nhìn theo ngành.</li>
              <li>Danh sách theo dõi cá nhân cơ bản.</li>
              <li>StockRadar AI Free theo giới hạn của tài khoản.</li>
              <li>Email hệ thống cần thiết cho xác minh và bảo mật tài khoản.</li>
            </ul>
            <p class="plan-price-note">Free không nhận báo cáo 09:00 hoặc cảnh báo điểm mua/bán trong phiên.</p>
            <a class="button button-secondary" href="signup/?plan=free" data-registration-plan="free">Đăng ký</a>
          </article>'''

    premium_card = '''<article class="plan-card plan-card-premium conversion-plan-card" data-plan-premium id="premium">
            <span class="plan-ribbon">ĐẦY ĐỦ TÍNH NĂNG</span>
            <span class="plan-kicker">199K / THÁNG</span>
            <h2>StockRadar Premium — 199K/tháng</h2>
            <div class="plan-price"><strong>199.000đ</strong><span>/ tháng</span></div>
            <p class="plan-summary">Dành cho người muốn có lớp quyết định đầy đủ, vùng hành động và cảnh báo khi trạng thái thay đổi.</p>
            <ul class="plan-feature-list">
              <li><strong>Mua mới:</strong> MUA / CHỜ theo từng khung.</li>
              <li><strong>Đang nắm giữ:</strong> GIỮ / TĂNG / GIẢM / BÁN.</li>
              <li><strong>Vùng hành động:</strong> Vùng mua · tỷ trọng · Stop · Target · Risk/Reward.</li>
              <li><strong>Báo cáo 09:00</strong> và cảnh báo thay đổi tại 10:30 · 11:15 · 13:30 · 14:15 khi đủ điều kiện.</li>
              <li><strong>My StockRadar:</strong> watchlist mở rộng và ưu tiên mã người dùng quan tâm.</li>
              <li><strong>StockRadar AI:</strong> không giới hạn câu hỏi theo quyền gói Premium.</li>
            </ul>
            <a class="button button-primary" href="signup/?plan=premium" data-registration-plan="premium" data-premium-conversion-cta data-conversion-action="plans_premium">Đăng ký</a>
            <p class="conversion-plan-note">Chu kỳ Premium hiện tại là 30 ngày, không tự gia hạn. Tạo và xác minh tài khoản trước khi sang bước thanh toán.</p>
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

    required = (
        'data-plan-free',
        'data-plan-premium',
        'href="signup/?plan=free" data-registration-plan="free">Đăng ký</a>',
        'href="signup/?plan=premium" data-registration-plan="premium"',
        '>Đăng ký</a>',
        '199K / THÁNG',
        '199.000đ',
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
    print(f"Locked registration plan CTAs: {page}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
