(() => {
  'use strict';

  const config = window.STOCKRADAR_AUTH_CONFIG || {};
  const transactionalAuthReady = Boolean(
    config.configured === true &&
    config.provider === 'supabase' &&
    config.supabaseUrl &&
    config.supabasePublishableKey
  );

  // emailDeliveryReady is the historical launch flag for email-dependent product UX.
  // Account verification/recovery is transactional auth and must not be coupled to
  // Premium content-email delivery readiness once Supabase Auth itself is configured.
  const productEmailLaunchState = config.emailDeliveryReady === true;
  void productEmailLaunchState;

  if (transactionalAuthReady) return;

  const BLOCKED_MESSAGE = 'Đăng ký mới đang tạm đóng vì dịch vụ xác thực tài khoản chưa được cấu hình đầy đủ. Đăng nhập tài khoản đã có chỉ hoạt động khi Supabase Auth sẵn sàng.';
  const RECOVERY_MESSAGE = 'Khôi phục mật khẩu đang tạm đóng vì dịch vụ xác thực tài khoản chưa sẵn sàng.';
  const BLOCKED_FORMS = '[data-auth-signup-form],[data-auth-signup-otp-form],[data-auth-login-otp-form],[data-auth-forgot-form]';

  function messageFor(form) {
    return form?.matches('[data-auth-forgot-form]') ? RECOVERY_MESSAGE : BLOCKED_MESSAGE;
  }

  function lock(form, message = messageFor(form)) {
    if (!form) return;
    form.dataset.emailDeliveryBlocked = 'true';
    form.querySelectorAll('input, button, select, textarea').forEach(control => {
      control.disabled = true;
    });
    const target = form.querySelector('[data-auth-message]');
    if (target) {
      target.className = 'auth-message error';
      if (target.textContent !== message) target.textContent = message;
    }
  }

  function enforce() {
    document.querySelectorAll(BLOCKED_FORMS).forEach(form => lock(form));

    const signupCard = document.querySelector('[data-auth-signup-form]')?.closest('.auth-card');
    if (signupCard && !signupCard.querySelector('[data-email-delivery-status]')) {
      const status = document.createElement('div');
      status.className = 'auth-email-gate';
      status.dataset.emailDeliveryStatus = '';
      status.setAttribute('role', 'status');
      status.innerHTML = '<strong>Đăng ký tạm đóng</strong><span>Dịch vụ xác thực tài khoản chưa được cấu hình đầy đủ.</span>';
      signupCard.prepend(status);
    }
  }

  document.addEventListener('submit', event => {
    const form = event.target.closest?.(BLOCKED_FORMS);
    if (!form) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    lock(form);
  }, true);

  document.addEventListener('click', event => {
    const button = event.target.closest?.('button');
    const form = button?.closest?.(BLOCKED_FORMS);
    if (!form) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    lock(form);
  }, true);

  document.addEventListener('DOMContentLoaded', enforce);
})();
