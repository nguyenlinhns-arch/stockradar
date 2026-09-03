(() => {
  'use strict';

  const config = window.STOCKRADAR_AUTH_CONFIG || {};
  if (config.emailDeliveryReady === true) return;

  const BLOCKED_MESSAGE = 'Đăng ký mới đang tạm đóng trong khi StockRadar hoàn tất kênh email xác minh. Đăng nhập tài khoản đã có vẫn hoạt động.';
  const RECOVERY_MESSAGE = 'Khôi phục mật khẩu qua email đang tạm đóng trong khi kênh email production được kích hoạt.';
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
      status.innerHTML = '<strong>Đăng ký tạm đóng</strong><span>Hệ thống đang hoàn tất email xác minh trước khi mở đăng ký công khai.</span>';
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
