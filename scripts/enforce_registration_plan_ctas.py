#!/usr/bin/env python3
"""Lock final StockRadar plan cards and direct signup flow after Pages transforms.

Commercial rule:
- Free: create account -> open Free account.
- Premium: create account -> pay 199,000 VND.
- Signup does not ask for OTP or email verification.
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
        <p>Premium: tạo tài khoản → thanh toán 199.000đ/30 ngày. Không cần tạo Free rồi mới nâng cấp.</p>
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
        'Tạo tài khoản xong chuyển thẳng sang thanh toán 199.000đ/30 ngày. Không có bước OTP hoặc xác minh email và không tự gia hạn.'
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
              <li>Email hệ thống cần thiết cho bảo mật tài khoản</li>
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


def enforce_signup_direct_flow(output: Path) -> Path:
    page = output / "signup" / "index.html"
    signup_client = output / "assets" / "signup-link-v1.js"
    for path in (page, signup_client):
        if not path.exists():
            raise FileNotFoundError(path)

    source = page.read_text(encoding="utf-8")
    source = re.sub(
        r'\s*<form class="auth-form auth-otp-panel"[^>]*data-auth-signup-otp-form.*?</form>\s*',
        "\n", source, flags=re.DOTALL,
    )
    source = re.sub(
        r'\s*<div class="auth-form auth-otp-panel"[^>]*data-signup-email-sent.*?</div>\s*',
        "\n", source, flags=re.DOTALL,
    )
    source = source.replace('EMAIL + PASSWORD + OTP', 'EMAIL + PASSWORD')
    source = source.replace('Tạo tài khoản Premium & gửi mã xác minh', 'Tạo tài khoản Premium & thanh toán')
    source = source.replace('Tạo tài khoản Free & gửi mã xác minh', 'Tạo tài khoản Free')
    source = source.replace('Tạo tài khoản Premium & gửi email xác minh', 'Tạo tài khoản Premium & thanh toán')
    source = source.replace('Tạo tài khoản Free & gửi email xác minh', 'Tạo tài khoản Free')
    source = source.replace('Bấm xác minh trong email', 'Tạo tài khoản')
    source = source.replace('bấm xác minh trong email', 'tạo tài khoản')
    source = source.replace(
        'Bước này chỉ tạo và xác minh tài khoản. Không tự thu phí, không tự gia hạn.',
        'Tạo tài khoản xong sẽ chuyển thẳng sang thanh toán Premium. Không tự gia hạn.',
    )
    source = source.replace(
        'Thanh toán chỉ ở bước riêng sau khi tài khoản được xác minh.',
        'Thanh toán chỉ ở bước riêng sau khi tạo tài khoản.',
    )
    source = source.replace('tài khoản được xác minh', 'tài khoản được tạo')
    source = source.replace('xác minh tài khoản', 'tạo tài khoản')

    source = source.replace(
        '<p class="auth-switch">Đã có tài khoản? <a href="dang-nhap/">Đăng nhập</a></p>',
        '<p class="auth-switch">Đã có tài khoản? <a href="dang-nhap/" data-signup-existing-login>Đăng nhập</a></p>',
        1,
    )

    required = (
        'assets/signup-link-v1.js',
        'data-auth-signup-form',
        'data-signup-existing-login',
        'Tạo tài khoản Free',
        'Premium',
    )
    for marker in required:
        if marker not in source:
            raise RuntimeError(f"Direct signup contract missing: {marker}")

    for forbidden in (
        'data-auth-signup-otp-form',
        'data-signup-email-sent',
        'autocomplete="one-time-code"',
        'Nhập mã OTP 6 số',
        'Kiểm tra email để xác minh tài khoản',
        'Đã xác minh? Đăng nhập',
        'xac-minh-email/',
        'gửi email xác minh',
        'Bước này chỉ tạo và xác minh tài khoản',
        'tài khoản được xác minh',
    ):
        if forbidden in source:
            raise RuntimeError(f"Verification UI leaked into final signup artifact: {forbidden}")

    client = signup_client.read_text(encoding="utf-8")
    for marker in (
        '/functions/v1/signup-link',
        'signInWithPassword',
        'window.location.replace(destinationFor(plan))',
        "'thanh-toan/?plan=premium'",
    ):
        if marker not in client:
            raise RuntimeError(f"Direct signup client missing: {marker}")
    for forbidden in ('showEmailSent', 'data-signup-email-sent', 'sr_pending_signup_email'):
        if forbidden in client:
            raise RuntimeError(f"Legacy verification client leaked: {forbidden}")

    page.write_text(source, encoding="utf-8")
    return page


def enforce(output: Path) -> tuple[Path, Path]:
    return enforce_plan_page(output), enforce_signup_direct_flow(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    plans, signup = enforce(args.output)
    print(f"Locked registration plans (checkout_ready={checkout_ready()}): {plans}")
    print(f"Locked direct signup without verification: {signup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
