(() => {
  'use strict';

  const config = window.STOCKRADAR_AUTH_CONFIG || {};
  if (config.emailDeliveryReady === true) return;

  document.documentElement.classList.add('auth-email-pending');

  const message = 'Tính năng này sử dụng email xác minh. Bạn có thể đăng ký quan tâm Premium để nhận thông tin mở quyền.';

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
    disableForm(form, 'Đăng ký tài khoản mới sử dụng email xác minh. Hãy đăng ký quan tâm Premium tại biểu mẫu quan tâm.');
    disableForm(document.querySelector('[data-auth-signup-otp-form]'));
    form.hidden = true;
    const otp = document.querySelector('[data-auth-signup-otp-form]');
    if (otp) otp.hidden = true;

    const intro = document.querySelector('.auth-intro');
    if (intro) {
      const h1 = intro.querySelector('h1');
      const p = intro.querySelector('p');
      if (h1) h1.innerHTML = 'StockRadar<br>Premium';
      if (p) p.innerHTML = `Để lại email tại <a href="${interestHref()}">Đăng ký quan tâm Premium</a> để nhận thông tin mở quyền tài khoản và báo cáo Premium.`;
      intro.querySelector('.auth-stepper')?.setAttribute('hidden', '');
      intro.querySelector('.auth-benefits')?.setAttribute('hidden', '');
    }

    const header = document.querySelector('.auth-card-header');
    if (header) {
      const pill = header.querySelector('.auth-config-pill');
      const title = header.querySelector('h2');
      const p = header.querySelector('p');
      if (pill) pill.textContent = 'PREMIUM';
      if (title) title.textContent = 'Đăng ký quan tâm Premium';
      if (p) p.innerHTML = `<a href="${interestHref()}">Mở biểu mẫu đăng ký quan tâm</a> để StockRadar ghi nhận email của bạn.`;
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
    note.innerHTML = `Đăng nhập bằng email và mật khẩu vẫn hoạt động. <a href="${interestHref()}">Đăng ký quan tâm Premium</a>.`;
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