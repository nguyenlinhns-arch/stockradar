(() => {
  'use strict';

  const CONSENT_VERSION = '2026-09-03';
  const VALID_PLANS = new Set(['free', 'premium']);

  function selectedPlan(form) {
    const value = String(form?.elements?.selected_plan?.value || 'free').trim().toLowerCase();
    return VALID_PLANS.has(value) ? value : 'free';
  }

  function formMetadata() {
    const form = document.querySelector('[data-auth-signup-form]');
    if (!form) return null;

    const dailyBrief = Boolean(form.elements.email_daily_brief?.checked);
    const eventAlerts = Boolean(form.elements.email_event_alerts?.checked);
    const termsAccepted = Boolean(form.elements.terms?.checked);

    return {
      selected_plan_interest: selectedPlan(form),
      terms_accepted: termsAccepted,
      terms_version: CONSENT_VERSION,
      privacy_accepted: termsAccepted,
      privacy_version: CONSENT_VERSION,
      product_email_consent: dailyBrief || eventAlerts,
      product_email_consent_version: CONSENT_VERSION,
      product_email_daily_brief: dailyBrief,
      product_email_event_alerts: eventAlerts,
    };
  }

  function syncPlanUi() {
    const form = document.querySelector('[data-auth-signup-form]');
    if (!form) return;

    const requested = new URLSearchParams(window.location.search).get('plan');
    if (requested && VALID_PLANS.has(requested.toLowerCase())) {
      const radio = form.querySelector(`input[name="selected_plan"][value="${requested.toLowerCase()}"]`);
      if (radio) radio.checked = true;
    }

    const render = () => {
      const plan = selectedPlan(form);
      const premium = plan === 'premium';
      const name = document.querySelector('[data-signup-plan-name]');
      const note = document.querySelector('[data-signup-plan-note]');
      const submit = document.querySelector('[data-signup-submit-label]');

      if (name) name.textContent = premium ? 'Premium' : 'Free';
      if (note) {
        note.textContent = premium
          ? 'Premium kế thừa bản rà soát 09:00 của Free và bổ sung cảnh báo điểm mua/bán trong phiên tại 10:30, 11:15, 13:30 và 14:15 khi tín hiệu đủ chuẩn. Giá sáng lập dự kiến 199.000đ/30 ngày; tạo tài khoản chưa phát sinh thanh toán.'
          : 'Free có phí 0đ và đủ quyền nhận bản rà soát thị trường cơ bản lúc 09:00 hằng ngày sau khi email được xác minh và bạn chọn đồng ý nhận.';
      }
      if (submit) submit.textContent = premium
        ? 'Tạo tài khoản Premium & gửi mã xác minh'
        : 'Tạo tài khoản Free & gửi mã xác minh';
    };

    form.querySelectorAll('input[name="selected_plan"]').forEach(input => input.addEventListener('change', render));
    render();
  }

  function patchSupabaseClientFactory() {
    const sdk = window.supabase;
    if (!sdk || typeof sdk.createClient !== 'function' || sdk.createClient.__stockradarSignupPatched) return;

    const originalCreateClient = sdk.createClient.bind(sdk);
    const patchedCreateClient = (...args) => {
      const client = originalCreateClient(...args);
      const originalSignUp = client?.auth?.signUp?.bind(client.auth);
      if (!originalSignUp || client.auth.signUp.__stockradarSignupPatched) return client;

      const patchedSignUp = async credentials => {
        const metadata = formMetadata();
        if (!metadata) return originalSignUp(credentials);
        const originalOptions = credentials?.options || {};
        return originalSignUp({
          ...credentials,
          options: {
            ...originalOptions,
            data: {
              ...(originalOptions.data || {}),
              ...metadata,
            },
          },
        });
      };
      patchedSignUp.__stockradarSignupPatched = true;
      client.auth.signUp = patchedSignUp;
      return client;
    };

    patchedCreateClient.__stockradarSignupPatched = true;
    sdk.createClient = patchedCreateClient;
  }

  document.addEventListener('DOMContentLoaded', () => {
    syncPlanUi();
    patchSupabaseClientFactory();
  }, { once: true });
})();