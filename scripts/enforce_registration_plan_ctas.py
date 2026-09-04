#!/usr/bin/env python3
"""Lock final StockRadar plan cards and email-link signup flow after Pages transforms.

Commercial rule:
- Free: create account -> confirm by clicking the email link -> open Free account.
- Premium: create account -> confirm by clicking the email link -> pay 199,000 VND.
- Signup never asks the customer to copy a six-digit OTP into the website.
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
PREMIUM_SIGNUP_HREF = "signup/?plan=premium&next=thanh-toan/%3Fplan%3Dpremium"


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
        <h1>Chọn Free hoặc đăng ký Premium</h1>
        <p>Premium: tạo tài khoản → bấm xác minh trong email → thanh toán 199.000đ/30 ngày. Không cần tạo Free rồi mới nâng cấp.</p>
      </div>
    </section>'''
    updated, count = re.subn(
        r'<section class="plans-hero">.*?</section>', hero, source,
        count=1, flags=re.DOTALL,
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
        'Tạo tài khoản, bấm xác minh trong email rồi chuyển thẳng sang thanh toán 199.000đ/30 ngày. Không cần nhập OTP và không tự gia hạn.'
        if ready else
        'StockRadar đang tạm dừng nhận thanh toán Premium mới. Bạn vẫn có thể tạo tài khoản để ghi nhận nhu cầu Premium.'
    )
    cta = 'Đăng ký & thanh toán' if ready else 'Đăng ký nhận thông báo'
    href = PREMIUM_SIGNUP_HREF if ready else 'signup/?plan=premium'
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
            <a class="button button-primary" href="{href}" data-registration-plan="premium" data-premium-conversion-cta data-conversion-action="plans_premium">{cta}</a>
          </article>'''


def enforce_plan_page(output: Path) -> Path:
    page = output / "dang-ky" / "index.html"
    if not page.exists():
        raise FileNotFoundError(page)
    source = _replace_hero(page.read_text(encoding="utf-8"))

    free_card = '''<article class="plan-card" data-plan-free>
            <span class="plan-kicker">MIỄN PHÍ</span>
            <h2>StockRadar Free</h2>
            <div class="plan-price"><strong>0đ</strong><span>/ tháng</span></div>
            <p class="plan-summary">Tra cứu và trải nghiệm StockRadar miễn phí. Nếu muốn Premium, bạn có thể đăng ký Premium trực tiếp, không phải đăng ký Free trước.</p>
            <ul class="plan-feature-list">
              <li>StockRadar AI Free: 10 câu/ngày sau khi đăng nhập</li>
              <li>Tra cứu cổ phiếu HOSE và xem dữ liệu công khai</li>
              <li>Radar và góc nhìn theo ngành</li>
              <li>Danh sách theo dõi cá nhân cơ bản</li>
              <li>Email hệ thống cần thiết cho xác minh và bảo mật tài khoản</li>
            </ul>
            <div class="plan-info-box">Free không nhận Daily 09:00 hoặc cảnh báo điểm mua/bán trong phiên.</div>
            <a class="button button-secondary" href="signup/?plan=free" data-registration-plan="free">Đăng ký Free</a>
          </article>'''

    source = _replace_card(source, r'<article class="plan-card" data-plan-free>.*?</article>', free_card, "Free")
    source = _replace_card(
        source,
        r'<article class="plan-card plan-card-premium[^\"]*"[^>]*data-plan-premium[^>]*>.*?</article>',
        premium_card(), "Premium",
    )
    source = _ensure_final_style(source)

    for marker in (
        'data-plan-free', 'data-plan-premium',
        'href="signup/?plan=free" data-registration-plan="free">Đăng ký Free</a>',
        'GÓI DỊCH VỤ', '199.000đ', '10 câu/ngày', 'plan-info-box', STYLE_MARKER,
    ):
        if marker not in source:
            raise RuntimeError(f"Registration plan contract missing: {marker}")

    if checkout_ready():
        for marker in (f'href="{PREMIUM_SIGNUP_HREF}"', '>Đăng ký & thanh toán</a>', 'không phải đăng ký Free trước'):
            if marker not in source:
                raise RuntimeError(f"Premium direct-payment CTA missing: {marker}")
    if "Thanh toán / Nâng Premium" in source or ">Tạo tài khoản Premium</a>" in source:
        raise RuntimeError("Legacy Premium CTA leaked into final registration page")
    if source.count('data-registration-plan=') != 2:
        raise RuntimeError("Final registration page must contain exactly two plan registration CTAs")

    page.write_text(source, encoding="utf-8")
    return page


def enforce_signup_email_link_flow(output: Path) -> Path:
    page = output / "signup" / "index.html"
    confirm = output / "xac-minh-email" / "index.html"
    signup_client = output / "assets" / "signup-link-v1.js"
    confirm_client = output / "assets" / "email-confirm-v1.js"
    for path in (page, confirm, signup_client, confirm_client):
        if not path.exists():
            raise FileNotFoundError(path)

    source = page.read_text(encoding="utf-8")
    # Final transforms must never revive the removed manual OTP panel.
    source = re.sub(
        r'\s*<form class="auth-form auth-otp-panel"[^>]*data-auth-signup-otp-form.*?</form>\s*',
        "\n", source, flags=re.DOTALL,
    )
    source = source.replace('EMAIL + PASSWORD + OTP', 'EMAIL + PASSWORD')
    source = source.replace('Tạo tài khoản Premium & gửi mã xác minh', 'Tạo tài khoản Premium & gửi email xác minh')
    source = source.replace('Tạo tài khoản Free & gửi mã xác minh', 'Tạo tài khoản Free & gửi email xác minh')

    # Keep the existing-account path plan-aware without adding an upgrade detour.
    source = source.replace(
        '<p class="auth-switch">Đã có tài khoản? <a href="dang-nhap/">Đăng nhập</a></p>',
        '<p class="auth-switch">Đã có tài khoản? <a href="dang-nhap/" data-signup-existing-login>Đăng nhập</a></p>',
        1,
    )

    required = (
        'assets/signup-link-v1.js',
        'data-signup-email-sent',
        'gửi email xác minh',
        'Không cần nhập mã OTP',
        'data-signup-existing-login',
    )
    for marker in required:
        if marker not in source:
            raise RuntimeError(f"Email-link signup contract missing: {marker}")

    for forbidden in ('data-auth-signup-otp-form', 'autocomplete="one-time-code"', 'Nhập mã OTP 6 số'):
        if forbidden in source:
            raise RuntimeError(f"Manual signup OTP leaked into final artifact: {forbidden}")

    confirm_source = confirm.read_text(encoding="utf-8")
    for marker in ('assets/email-confirm-v1.js', 'Không cần nhập mã OTP', 'data-email-confirm-status'):
        if marker not in confirm_source:
            raise RuntimeError(f"Email confirmation route missing: {marker}")

    page.write_text(source, encoding="utf-8")
    return page


def enforce(output: Path) -> tuple[Path, Path]:
    return enforce_plan_page(output), enforce_signup_email_link_flow(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    plans, signup = enforce(args.output)
    print(f"Locked registration plans (checkout_ready={checkout_ready()}): {plans}")
    print(f"Locked no-OTP email-link signup flow: {signup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
