(() => {
  'use strict';

  function siteUrl(path) {
    return new URL(String(path || '').replace(/^\/+/, ''), document.baseURI).toString();
  }

  function normalizeHeader() {
    document.querySelectorAll('.header-register-cta').forEach(link => {
      link.href = siteUrl('dang-ky/?plan=free');
      link.textContent = 'Bắt đầu miễn phí';
    });
  }

  function normalizeSignup() {
    const form = document.querySelector('[data-auth-signup-form]');
    if (!form) return;
    const render = () => {
      const plan = String(form.elements.selected_plan?.value || 'free').toLowerCase();
      const premium = plan === 'premium';
      const note = document.querySelector('[data-signup-plan-note]');
      if (note) note.textContent = premium
        ? 'Premium · AI không giới hạn · 199.000đ/30 ngày.'
        : 'Free · AI 10 câu/ngày.';
      const emailNote = document.querySelector('.signup-email-note');
      if (emailNote) emailNote.textContent = premium
        ? 'Có thể bật/tắt Daily 09:00 và Action Alert.'
        : 'Email nội dung chỉ dành cho Premium.';
      const locked = document.querySelector('[data-signup-locked-plan]');
      if (locked) locked.textContent = premium
        ? 'Premium · 199.000đ/30 ngày'
        : 'Free · 0đ';
    };
    form.querySelectorAll('input[name="selected_plan"]').forEach(input => input.addEventListener('change', render));
    render();
  }

  function normalizeStock() {
    const intro = document.querySelector('.commercial-stock-page .stock-analysis-intro');
    if (intro) intro.textContent = 'Mua mới · Nắm giữ · Vùng giá · Rủi ro.';
  }

  function normalizeLogin() {
    document.querySelectorAll('.commercial-auth-page .auth-switch a[href*="signup/"]').forEach(link => {
      link.href = siteUrl('dang-ky/?plan=free');
      link.textContent = 'Bắt đầu miễn phí';
    });
  }

  function normalize() {
    normalizeHeader();
    normalizeSignup();
    normalizeStock();
    normalizeLogin();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', normalize, { once: true });
  else normalize();
  setTimeout(normalize, 80);
  setTimeout(normalize, 500);
})();
