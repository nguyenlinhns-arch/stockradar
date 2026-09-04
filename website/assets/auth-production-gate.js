(() => {
  'use strict';

  const config = window.STOCKRADAR_AUTH_CONFIG || {};
  const transactionalAuthReady = Boolean(
    config.configured === true &&
    config.provider === 'supabase' &&
    config.supabaseUrl &&
    config.supabasePublishableKey
  );

  // Account registration/login/OTP are transactional Supabase Auth features.
  // They must remain available even while Premium content-email delivery is
  // still gated separately by emailDeliveryReady.
  if (transactionalAuthReady) {
    document.documentElement.classList.remove('auth-email-pending');
    return;
  }

  document.documentElement.classList.add('auth-email-pending');

  const message = 'Dịch vụ xác thực tài khoản chưa được cấu hình đầy đủ.';

  function disableForm(form, customMessage = message) {
    if (!form || form.dataset.emailGateLocked === '1') return;
    form.dataset.emailGateLocked = '1';
    form.setAttribute('data-email-gate-locked', '');
    form.querySelectorAll('input, button, select, textarea').forEach(control => { control.disabled = true; });
    const target = form.querySelector('[data-auth-message], [data-form-message]');
    if (target) {
      target.className = target.classList.contains('form-message') ? 'form-message error' : 'auth-message error';
      target.textContent = customMessage;
    }
  }

  function interestHref() {
    return new URL('dang-ky/', document.baseURI).href;
  }

  function patchSignupPage() {
    const form = document.querySelector('[data-auth-signup-form]');
    if (!form) return;
    disableForm(form, 'Đăng ký tài khoản đang tạm dừng vì Supabase Auth chưa được cấu hình đầy đủ.');
    disableForm(document.querySelector('[data-auth-signup-otp-form]'));

    const intro = document.querySelector('.auth-intro');
    if (intro) {
      const p = intro.querySelector('p');
      if (p) p.innerHTML = `Dịch vụ tạo tài khoản đang tạm dừng. Bạn vẫn có thể xem các gói tại <a href="${interestHref()}">Free / Premium</a>.`;
    }
  }

  function patchLoginPage() {
    const login = document.querySelector('[data-auth-login-form]');
    if (!login) return;
    disableForm(login, 'Đăng nhập đang tạm dừng vì Supabase Auth chưa được cấu hình đầy đủ.');
    document.querySelectorAll('[data-auth-login-otp-form], [data-auth-forgot-form]').forEach(form => disableForm(form));
  }

  function applyGate() {
    patchSignupPage();
    patchLoginPage();
  }

  document.addEventListener('DOMContentLoaded', applyGate, { once: true });
})();
