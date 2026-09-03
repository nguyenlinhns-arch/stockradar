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

  function interestHref() {
    return new URL('dang-ky/', document.baseURI).href;
  }

  function patchSignupPage() {
    const form = document.querySelector('[data-auth-signup-form]');
    if (!form) return;
    disableForm(form, 'Tạo tài khoản mới đang tạm khóa cho đến khi email xác minh hoạt động ổn định.');
    disableForm(document.querySelector('[data-auth-signup-otp-form]'), 'Xác minh OTP đang tạm khóa cùng luồng đăng ký mới.');

    const intro = document.querySelector('.auth-intro');
    if (intro) {
      const h1 = intro.querySelector('h1');
      const p = intro.querySelector('p');
      if (h1) h1.innerHTML = 'Tạo tài khoản mới<br>đang tạm khóa.';
      if (p) p.innerHTML = `Email xác minh production đang được hoàn thiện. Bạn vẫn có thể <a href="${interestHref()}">đăng ký quan tâm Premium</a> để StockRadar ghi nhận nhu cầu trước.`;
      intro.querySelector('.auth-stepper')?.setAttribute('hidden', '');
      intro.querySelector('.auth-benefits')?.setAttribute('hidden', '');
    }

    const header = document.querySelector('.auth-card-header');
    if (header) {
      const pill = header.querySelector('.auth-config-pill');
      const title = header.querySelector('h2');
      const p = header.querySelector('p');
      if (pill) pill.textContent = 'CHỜ EMAIL XÁC MINH';
      if (title) title.textContent = 'Tạo tài khoản';
      if (p) p.innerHTML = `Trong thời gian chờ, <a href="${interestHref()}">ghi nhận email quan tâm Premium</a> mà không kích hoạt gửi nội dung.`;
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

  function routeSignupLinksToInterest() {
    document.querySelectorAll('a[href$="signup/"], a[href*="/signup/"]').forEach(link => {
      if (link.closest('[data-auth-signup-form], [data-auth-signup-otp-form]')) return;
      link.href = interestHref();
      if (link.classList.contains('header-register-cta')) link.textContent = 'Đăng ký';
      if (/Đăng ký Premium|Tạo tài khoản|Đăng ký StockRadar/i.test(link.textContent || '')) {
        link.textContent = 'Đăng ký quan tâm';
      }
    });
  }

  function addGateNote() {
    if (!document.querySelector('[data-auth-login-form]') || document.querySelector('[data-auth-email-gate-note]')) return;
    const card = document.querySelector('.auth-card');
    if (!card) return;
    const note = document.createElement('p');
    note.className = 'auth-email-gate-note';
    note.dataset.authEmailGateNote = '';
    note.innerHTML = `Đăng nhập bằng mật khẩu vẫn hoạt động. Đăng ký mới, gửi lại OTP và khôi phục mật khẩu qua email đang tạm khóa. <a href="${interestHref()}">Đăng ký quan tâm Premium</a>.`;
    card.append(note);
  }

  let scheduled = false;
  function applyGate() {
    patchSignupPage();
    patchLoginPage();
    routeSignupLinksToInterest();
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