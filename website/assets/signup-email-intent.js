(() => {
  'use strict';

  const TERMS_VERSION = '2026-09-03';
  const PRIVACY_VERSION = '2026-09-04';
  const PRODUCT_EMAIL_CONSENT_VERSION = '2026-09-04';
  const VALID_PLANS = new Set(['free', 'premium']);
  const PENDING_LEAD_EMAIL_KEY = 'sr_pending_lead_email';

  function selectedPlan(form) {
    const value = String(form?.elements?.selected_plan?.value || 'free').trim().toLowerCase();
    return VALID_PLANS.has(value) ? value : 'free';
  }

  function pendingLeadEmail() {
    try { return String(sessionStorage.getItem(PENDING_LEAD_EMAIL_KEY) || '').trim().toLowerCase(); } catch (_) { return ''; }
  }

  function clearPendingLeadEmail() {
    try { sessionStorage.removeItem(PENDING_LEAD_EMAIL_KEY); } catch (_) {}
  }

  function formMetadata() {
    const form = document.querySelector('[data-auth-signup-form]');
    if (!form) return null;
    const plan = selectedPlan(form);
    const premiumIntent = plan === 'premium';
    const dailyBrief = Boolean(premiumIntent && form.elements.email_daily_brief?.checked);
    const eventAlerts = Boolean(premiumIntent && form.elements.email_event_alerts?.checked);
    const termsAccepted = Boolean(form.elements.terms?.checked);
    return {
      selected_plan_interest: plan,
      terms_accepted: termsAccepted,
      terms_version: TERMS_VERSION,
      privacy_accepted: termsAccepted,
      privacy_version: PRIVACY_VERSION,
      product_email_consent: premiumIntent && (dailyBrief || eventAlerts),
      product_email_consent_version: PRODUCT_EMAIL_CONSENT_VERSION,
      product_email_daily_brief: dailyBrief,
      product_email_event_alerts: eventAlerts,
    };
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
      clearPendingLeadEmail();
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
      const emailNote = document.querySelector('.signup-email-note');
      const submit = document.querySelector('[data-signup-submit-label]');
      const daily = form.elements.email_daily_brief;
      const alerts = form.elements.email_event_alerts;

      if (name) name.textContent = premium ? 'Premium' : 'Free';
      if (note) {
        note.textContent = premium
          ? 'Premium: email tự động cập nhật điểm mua/bán của mã theo dõi, bản tin 09:00 và AI không giới hạn. Giá 199.000đ/30 ngày.'
          : 'Free có phí 0đ, StockRadar AI 10 câu/ngày và email hệ thống cần thiết cho tài khoản. Báo cáo hằng ngày và Action Alert thuộc Premium.';
      }
      if (emailNote) {
        emailNote.textContent = premium
          ? 'Tùy chọn bản tin 09:00 và email điểm mua/bán. Kênh gửi chưa bật; bạn có thể bỏ chọn từng loại email.'
          : 'Email nội dung chỉ áp dụng cho Premium. Free chỉ nhận email hệ thống cần thiết cho tài khoản.';
      }
      [daily, alerts].forEach(input => {
        if (!input) return;
        input.disabled = !premium;
        if (!premium) {
          input.checked = false;
        } else if (input.dataset.userTouched !== '1') {
          input.checked = true;
        }
      });
      if (submit) submit.textContent = premium
        ? 'Tạo tài khoản Premium & thanh toán'
        : 'Tạo tài khoản Free';
    };

    [form.elements.email_daily_brief, form.elements.email_event_alerts].forEach(input => {
      if (!input) return;
      input.addEventListener('change', () => { input.dataset.userTouched = '1'; });
    });
    form.querySelectorAll('input[name="selected_plan"]').forEach(input => input.addEventListener('change', render));
    render();
  }

  window.STOCKRADAR_SIGNUP_METADATA = formMetadata;
  document.addEventListener('DOMContentLoaded', syncPlanUi, { once: true });
})();
