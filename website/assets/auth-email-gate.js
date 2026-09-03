(() => {
  'use strict';

  const config = window.STOCKRADAR_AUTH_CONFIG || {};
  if (config.emailDeliveryReady === true) return;

  const BLOCKED_MESSAGE = 'Đăng ký mới đang tạm đóng trong khi StockRadar hoàn tất kênh email xác minh. Đăng nhập tài khoản đã có vẫn hoạt động.';
  const RECOVERY_MESSAGE = 'Khôi phục mật khẩu qua email đang tạm đóng trong khi kênh email production được kích hoạt.';

  function lock(form, message) {
    if (!form) return;
    form.dataset.emailDeliveryBlocked = 'true';
    form.querySelectorAll('input, button, select, textarea').forEach(control => {
      control.disabled = true;
    });
    const target = form.querySelector('[data-auth-message]');
    if (target) {
      target.className = 'auth-message error';
      target.textContent = message;
    }
  }

  function enforce() {
    lock(document.querySelector('[data-auth-signup-form]'), BLOCKED_MESSAGE);
    lock(document.querySelector('[data-auth-signup-otp-form]'), BLOCKED_MESSAGE);
    lock(document.querySelector('[data-auth-login-otp-form]'), BLOCKED_MESSAGE);
    lock(document.querySelector('[data-auth-forgot-form]'), RECOVERY_MESSAGE);

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

  document.addEventListener('DOMContentLoaded', () => {
    enforce();
    const observer = new MutationObserver(enforce);
    observer.observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ['hidden'] });
  });
})();
