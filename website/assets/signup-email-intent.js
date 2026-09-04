(() => {
  'use strict';

  const VALID_PLANS = new Set(['free', 'premium']);
  const PENDING_LEAD_EMAIL_KEY = 'sr_pending_lead_email';

  function selectedPlan(form) {
    const value = String(form?.elements?.selected_plan?.value || 'free').trim().toLowerCase();
    return VALID_PLANS.has(value) ? value : 'free';
  }

  function pendingLeadEmail() {
    try { return String(sessionStorage.getItem(PENDING_LEAD_EMAIL_KEY) || '').trim().toLowerCase(); } catch (_) { return ''; }
  }

  function syncPlanUi() {
    const form = document.querySelector('[data-auth-signup-form]');
    if (!form) return;

    const params = new URLSearchParams(window.location.search);
    const requested = params.get('plan');
    const queryEmail = String(params.get('email') || '').trim().toLowerCase();
    const presetEmail = queryEmail || pendingLeadEmail();

    if (requested && VALID_PLANS.has(requested.toLowerCase())) {
      const radio = form.querySelector(`input[name="selected_plan"][value="${requested.toLowerCase()}"]`);
      if (radio) radio.checked = true;
    }

    const lockedPlan = requested && VALID_PLANS.has(requested.toLowerCase()) ? requested.toLowerCase() : '';
    const selector = form.querySelector('.signup-plan-selector');
    if (selector && lockedPlan) {
      selector.hidden = true;
      selector.dataset.planLocked = lockedPlan;
      if (!form.querySelector('[data-signup-locked-plan]')) {
        const summary = document.createElement('div');
        summary.className = 'signup-plan-note signup-locked-plan';
        summary.dataset.signupLockedPlan = lockedPlan;
        summary.textContent = lockedPlan === 'premium'
          ? 'Đang đăng ký Premium · 199.000đ/30 ngày · StockRadar AI không giới hạn. Tạo tài khoản xong sẽ chuyển thẳng sang thanh toán.'
          : 'Đang đăng ký Free · 0đ · StockRadar AI 10 câu/ngày. Tạo tài khoản xong sẽ mở trang tài khoản.';
        selector.before(summary);
      }
    }

    if (presetEmail && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(presetEmail) && form.elements.email && !form.elements.email.value) {
      form.elements.email.value = presetEmail;
    }

    if (queryEmail && window.history?.replaceState) {
      params.delete('email');
      const cleanQuery = params.toString();
      const cleanUrl = `${window.location.pathname}${cleanQuery ? `?${cleanQuery}` : ''}${window.location.hash || ''}`;
      window.history.replaceState(null, '', cleanUrl);
    }

    const render = () => {
      const plan = selectedPlan(form);
      const premium = plan === 'premium';
      const name = document.querySelector('[data-signup-plan-name]');
      const note = document.querySelector('[data-signup-plan-note]');
      const submit = document.querySelector('[data-signup-submit-label]');
      const daily = form.elements.email_daily_brief;
      const alerts = form.elements.email_event_alerts;

      if (name) name.textContent = premium ? 'Premium' : 'Free';
      if (note) {
        note.textContent = premium
          ? 'Premium mở StockRadar AI không giới hạn, Daily 09:00, kế hoạch giao dịch và Action Alert trong phiên khi dữ liệu đủ chuẩn. Giá 199.000đ/30 ngày.'
          : 'Free có phí 0đ, StockRadar AI 10 câu/ngày và dùng các chức năng công khai. Báo cáo hằng ngày và Action Alert thuộc Premium.';
      }
      [daily, alerts].forEach(input => {
        if (!input) return;
        input.disabled = !premium;
        if (!premium) input.checked = false;
      });
      if (submit) submit.textContent = premium
        ? 'Tạo tài khoản Premium & thanh toán'
        : 'Tạo tài khoản Free';
    };

    form.querySelectorAll('input[name="selected_plan"]').forEach(input => input.addEventListener('change', render));
    render();
  }

  document.addEventListener('DOMContentLoaded', syncPlanUi, { once: true });
})();
