#!/usr/bin/env python3
"""Lock final StockRadar registration and Premium payment flow after Pages transforms.

Commercial rule:
- Free registration remains free and opens the account after email verification.
- Premium registration is one continuous journey: choose Premium -> create account
  -> verify email -> pay 199,000 VND -> activate only after verified payment.
- Existing signed-in users who enter the Premium signup route go straight to
  checkout instead of being forced through an "upgrade" detour.
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
PREMIUM_LOGIN_HREF = "dang-nhap/?next=thanh-toan/%3Fplan%3Dpremium"
PREMIUM_CHECKOUT_PATH = "thanh-toan/?plan=premium"
SIGNUP_FLOW_MARKER = "data-premium-signup-payment-flow-v1"


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
        <p>Premium: tạo tài khoản → xác minh email → thanh toán 199.000đ/30 ngày. Không cần tạo Free rồi mới nâng cấp.</p>
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
        'Đăng ký Premium là một luồng liền mạch: tạo tài khoản, xác minh email rồi chuyển thẳng sang thanh toán 199.000đ/30 ngày. Không tự gia hạn.'
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

    source = page.read_text(encoding="utf-8")
    source = _replace_hero(source)

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
        'href="signup/?plan=free" data-registration-plan="free">Đăng ký Free</a>',
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
        for marker in (
            f'href="{PREMIUM_SIGNUP_HREF}"',
            '>Đăng ký & thanh toán</a>',
            'không phải đăng ký Free trước',
        ):
            if marker not in source:
                raise RuntimeError(f"Premium direct-payment CTA missing: {marker}")
        for stale in ('Đăng ký nhận thông báo', 'TẠM DỪNG KÍCH HOẠT MỚI'):
            if stale in source:
                raise RuntimeError(f"Stale paused Premium CTA leaked into open checkout: {stale}")
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


def _premium_signup_inline_script() -> str:
    return f'''<script {SIGNUP_FLOW_MARKER}>
(() => {{
  'use strict';
  const checkoutPath = '{PREMIUM_CHECKOUT_PATH}';
  const premiumLoginHref = '{PREMIUM_LOGIN_HREF}';
  const params = new URLSearchParams(window.location.search);
  let redirecting = false;

  function selectedPlan() {{
    const requested = String(params.get('plan') || '').trim().toLowerCase();
    if (requested === 'premium' || requested === 'free') return requested;
    const selected = String(document.querySelector('input[name="selected_plan"]:checked')?.value || 'free').trim().toLowerCase();
    return selected === 'premium' ? 'premium' : 'free';
  }}

  function syncCopy() {{
    const premium = selectedPlan() === 'premium';
    const step = document.querySelector('[data-signup-final-step]');
    if (step) step.innerHTML = premium ? '<b>3</b>Thanh toán Premium' : '<b>3</b>Mở tài khoản Free';

    const otpSubmit = document.querySelector('[data-signup-otp-submit]');
    if (otpSubmit) otpSubmit.textContent = premium ? 'Xác minh & sang thanh toán' : 'Xác minh & mở tài khoản';

    const existingLogin = document.querySelector('[data-signup-existing-login]');
    if (existingLogin) existingLogin.setAttribute('href', premium ? premiumLoginHref : 'dang-nhap/');

    const summary = document.querySelector('[data-premium-flow-summary] span');
    if (summary && premium) summary.textContent = 'Xác minh email xong sẽ chuyển thẳng sang thanh toán 199.000đ/30 ngày. Không cần tạo Free rồi nâng cấp.';

    const note = document.querySelector('[data-signup-otp-note]');
    if (note && !note.classList.contains('error') && !note.classList.contains('success')) {{
      note.textContent = premium
        ? 'Sau khi OTP hợp lệ, StockRadar chuyển thẳng tới thanh toán Premium. Quyền Premium chỉ kích hoạt sau khi tiền được xác nhận.'
        : 'Sau khi OTP hợp lệ, tài khoản Free được mở ngay.';
    }}
  }}

  async function redirectExistingPremiumUser() {{
    if (redirecting || selectedPlan() !== 'premium') return;
    const cfg = window.STOCKRADAR_AUTH_CONFIG || {{}};
    if (!cfg.configured || !cfg.supabaseUrl || !cfg.supabasePublishableKey || !window.supabase?.createClient) return;
    try {{
      const client = window.supabase.createClient(
        String(cfg.supabaseUrl).replace(/\\/+$/, ''),
        String(cfg.supabasePublishableKey),
        {{ auth: {{ persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, storageKey: 'stockradar-auth' }} }}
      );
      const {{ data }} = await client.auth.getUser();
      if (data?.user?.email_confirmed_at) {{
        redirecting = true;
        window.location.replace(new URL(checkoutPath, document.baseURI).toString());
      }}
    }} catch (_) {{}}
  }}

  document.addEventListener('DOMContentLoaded', () => {{
    syncCopy();
    document.querySelectorAll('input[name="selected_plan"]').forEach((input) => {{
      input.addEventListener('change', () => {{
        syncCopy();
        redirectExistingPremiumUser();
      }});
    }});
    if (String(params.get('plan') || '').trim().toLowerCase() === 'premium') redirectExistingPremiumUser();
  }}, {{ once: true }});
}})();
</script>'''


def enforce_signup_payment_flow(output: Path) -> Path:
    page = output / "signup" / "index.html"
    if not page.exists():
        raise FileNotFoundError(page)

    source = page.read_text(encoding="utf-8")
    source = re.sub(
        r'<span class="auth-step"><b>3</b>.*?</span>',
        '<span class="auth-step" data-signup-final-step><b>3</b>Thanh toán Premium / mở Free</span>',
        source,
        count=1,
        flags=re.DOTALL,
    )
    source = source.replace(
        'Chọn gói trước, sau đó nhập thông tin tài khoản. Việc tạo tài khoản không tự phát sinh thanh toán.',
        'Chọn gói trước rồi tạo tài khoản. Nếu chọn Premium, xác minh email xong sẽ chuyển thẳng sang thanh toán 199.000đ/30 ngày.',
        1,
    )
    source = re.sub(
        r'<div class="conversion-premium-summary" data-premium-flow-summary hidden>.*?</div>',
        '<div class="conversion-premium-summary" data-premium-flow-summary hidden><strong>Bạn đang đăng ký StockRadar Premium · 199.000đ/30 ngày</strong><span>Xác minh email xong sẽ chuyển thẳng sang thanh toán. Không cần tạo Free rồi nâng cấp.</span></div>',
        source,
        count=1,
        flags=re.DOTALL,
    )
    source = re.sub(
        r'<button class="button button-primary" type="submit">Xác minh &amp; mở Tài khoản</button>',
        '<button class="button button-primary" type="submit" data-signup-otp-submit>Xác minh &amp; tiếp tục</button>',
        source,
        count=1,
    )
    source = re.sub(
        r'<p class="auth-message" data-auth-message aria-live="polite">Sau khi xác minh, Free dùng StockRadar AI 10 câu/ngày.*?</p>',
        '<p class="auth-message" data-auth-message data-signup-otp-note aria-live="polite">Sau khi OTP hợp lệ, StockRadar sẽ tiếp tục theo đúng gói bạn đã chọn.</p>',
        source,
        count=1,
        flags=re.DOTALL,
    )
    source = source.replace(
        '<p class="auth-switch">Đã có tài khoản? <a href="dang-nhap/">Đăng nhập</a></p>',
        '<p class="auth-switch">Đã có tài khoản? <a href="dang-nhap/" data-signup-existing-login>Đăng nhập</a></p>',
        1,
    )

    if SIGNUP_FLOW_MARKER not in source:
        if "</body>" not in source:
            raise RuntimeError("Signup page has no closing body tag")
        source = source.replace("</body>", _premium_signup_inline_script() + "\n</body>", 1)

    required = (
        'data-signup-final-step',
        'data-signup-otp-submit',
        'data-signup-existing-login',
        SIGNUP_FLOW_MARKER,
        PREMIUM_CHECKOUT_PATH,
        PREMIUM_LOGIN_HREF,
        'Xác minh email xong sẽ chuyển thẳng sang thanh toán',
        'Không cần tạo Free rồi nâng cấp',
    )
    for marker in required:
        if marker not in source:
            raise RuntimeError(f"Premium signup payment-flow contract missing: {marker}")

    page.write_text(source, encoding="utf-8")
    return page


def enforce(output: Path) -> tuple[Path, Path]:
    return enforce_plan_page(output), enforce_signup_payment_flow(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    plans, signup = enforce(args.output)
    print(f"Locked registration plans (checkout_ready={checkout_ready()}): {plans}")
    print(f"Locked Premium signup -> payment flow: {signup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
