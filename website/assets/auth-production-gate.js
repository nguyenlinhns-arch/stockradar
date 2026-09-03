(() => {
  'use strict';

  const config = window.STOCKRADAR_AUTH_CONFIG || {};
  if (config.emailDeliveryReady === true) return;

  document.documentElement.classList.add('auth-email-pending');

  const message = 'Đăng ký mới và khôi phục qua email đang tạm thời chưa khả dụng trong khi hệ thống email xác minh được hoàn thiện.';

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

  function patchSignupPage() {
    const form = document.querySelector('[data-auth-signup-form]');
    if (!form) return;
    disableForm(form, 'Đăng ký mới đang tạm khóa cho đến khi email xác minh hoạt động ổn định.');
    disableForm(document.querySelector('[data-auth-signup-otp-form]'), 'Xác minh OTP đang tạm khóa cùng luồng đăng ký mới.');

    const intro = document.querySelector('.auth-intro');
    if (intro) {
      const h1 = intro.querySelector('h1');
      const p = intro.querySelector('p');
      if (h1) h1.innerHTML = 'Đăng ký mới<br>đang tạm khóa.';
      if (p) p.textContent = 'StockRadar chỉ mở đăng ký công khai sau khi email xác minh hoạt động ổn định và được kiểm tra đầy đủ.';
      intro.querySelector('.auth-stepper')?.setAttribute('hidden', '');
      intro.querySelector('.auth-benefits')?.setAttribute('hidden', '');
    }

    const header = document.querySelector('.auth-card-header');
    if (header) {
      const pill = header.querySelector('.auth-config-pill');
      const title = header.querySelector('h2');
      const p = header.querySelector('p');
      if (pill) pill.textContent = 'TẠM CHƯA MỞ';
      if (title) title.textContent = 'Đăng ký';
      if (p) p.textContent = 'Tài khoản mới sẽ được mở lại ngay khi luồng email xác minh sẵn sàng.';
    }
  }

  function patchLoginPage() {
    const login = document.querySelector('[data-auth-login-form]');
    if (!login) return;

    document.querySelectorAll('[data-auth-login-otp-form], [data-auth-forgot-form]').forEach(form => {
      disableForm(form);
      const details = form.closest('details');
      if (details) details.hidden = true;
    });

    const intro = document.querySelector('.auth-intro');
    if (intro) {
      const p = intro.querySelector('p');
      if (p) p.textContent = 'Dùng email và mật khẩu đã đăng ký để truy cập tài khoản StockRadar.';
      const benefits = intro.querySelector('.auth-benefits');
      if (benefits) benefits.innerHTML = '<li>Giữ phiên đăng nhập trên thiết bị hiện tại.</li><li>Thông tin tài khoản được bảo vệ bởi Supabase Auth.</li>';
    }
  }

  function removeSignupLinks() {
    document.querySelectorAll('a[href$="signup/"], a[href*="/signup/"]').forEach(link => {
      if (link.closest('[data-auth-account]')) return;
      link.hidden = true;
    });
  }

  function addGateNote() {
    if (!document.querySelector('[data-auth-login-form]') || document.querySelector('[data-auth-email-gate-note]')) return;
    const card = document.querySelector('.auth-card');
    if (!card) return;
    const note = document.createElement('p');
    note.className = 'auth-email-gate-note';
    note.dataset.authEmailGateNote = '';
    note.textContent = 'Đăng nhập bằng mật khẩu vẫn hoạt động. Đăng ký mới, gửi lại OTP và khôi phục mật khẩu qua email đang tạm khóa.';
    card.append(note);
  }

  let scheduled = false;
  function applyGate() {
    patchSignupPage();
    patchLoginPage();
    removeSignupLinks();
    addGateNote();
  }

  function scheduleGate() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      applyGate();
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    applyGate();
    const observer = new MutationObserver(scheduleGate);
    observer.observe(document.body, { childList: true, subtree: true });
  });
})();
