(() => {
  'use strict';

  const TERMS_VERSION = '2026-09-03';
  const PRIVACY_VERSION = '2026-09-04';
  const CONSENT_VERSION = '2026-09-04';

  function normalizeEmail(value) {
    return String(value || '').trim().toLowerCase();
  }

  function selectedPlan(form) {
    const value = String(form?.elements?.selected_plan?.value || 'free').trim().toLowerCase();
    return value === 'premium' ? 'premium' : 'free';
  }

  function setMessage(target, message, kind = '') {
    if (!target) return;
    target.className = `auth-message${kind ? ` ${kind}` : ''}`;
    target.textContent = message;
  }

  function setBusy(form, busy, label = 'Đang xử lý…') {
    const button = form?.querySelector('button[type="submit"]');
    if (!button) return;
    if (!button.dataset.defaultLabel) button.dataset.defaultLabel = button.textContent.trim();
    button.disabled = busy;
    button.textContent = busy ? label : button.dataset.defaultLabel;
  }

  function maskEmail(email) {
    const [local, domain] = normalizeEmail(email).split('@');
    if (!local || !domain) return email;
    const visible = local.length <= 2 ? local.slice(0, 1) : local.slice(0, 2);
    return `${visible}***@${domain}`;
  }

  function destinationFor(plan) {
    return new URL(plan === 'premium' ? 'thanh-toan/?plan=premium' : 'tai-khoan/?verified=1', document.baseURI).toString();
  }

  function syncExistingLogin(form) {
    const link = document.querySelector('[data-signup-existing-login]');
    if (!link) return;
    const next = selectedPlan(form) === 'premium' ? 'thanh-toan/?plan=premium' : 'tai-khoan/';
    link.href = `dang-nhap/?next=${encodeURIComponent(next)}`;
  }

  async function redirectExistingPremiumUser(form) {
    if (selectedPlan(form) !== 'premium') return false;
    const cfg = window.STOCKRADAR_AUTH_CONFIG || {};
    if (!cfg.configured || !cfg.supabaseUrl || !cfg.supabasePublishableKey || !window.supabase?.createClient) return false;
    try {
      const client = window.supabase.createClient(
        String(cfg.supabaseUrl).replace(/\/$/, ''),
        String(cfg.supabasePublishableKey),
        { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, storageKey: 'stockradar-auth' } },
      );
      const { data } = await client.auth.getUser();
      if (data?.user?.email_confirmed_at) {
        window.location.replace(destinationFor('premium'));
        return true;
      }
    } catch (_) {}
    return false;
  }

  function showEmailSent(form, panel, email, plan) {
    form.hidden = true;
    panel.hidden = false;
    const address = panel.querySelector('[data-signup-email-sent-address]');
    const title = panel.querySelector('[data-signup-email-sent-title]');
    const copy = panel.querySelector('[data-signup-email-sent-copy]');
    const login = panel.querySelector('[data-signup-email-open-login]');
    if (address) address.textContent = maskEmail(email);
    if (title) title.textContent = 'Kiểm tra email để xác minh tài khoản';
    if (copy) {
      copy.textContent = plan === 'premium'
        ? 'Bấm nút “Xác minh email StockRadar” trong email. Xác minh xong hệ thống sẽ đưa bạn thẳng tới thanh toán Premium 199.000đ/30 ngày.'
        : 'Bấm nút “Xác minh email StockRadar” trong email. Xác minh xong tài khoản Free sẽ được mở.';
    }
    if (login) {
      const next = encodeURIComponent(plan === 'premium' ? 'thanh-toan/?plan=premium' : 'tai-khoan/');
      login.href = `dang-nhap/?next=${next}`;
    }
  }

  async function submitSignup(event, form, panel) {
    event.preventDefault();
    event.stopImmediatePropagation();

    const message = form.querySelector('[data-auth-message]');
    const email = normalizeEmail(form.elements.email?.value);
    const password = String(form.elements.password?.value || '');
    const confirm = String(form.elements.password_confirm?.value || '');
    const terms = Boolean(form.elements.terms?.checked);
    const plan = selectedPlan(form);

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return setMessage(message, 'Nhập email hợp lệ.', 'error');
    if (password.length < 8 || password.length > 128) return setMessage(message, 'Mật khẩu cần từ 8 đến 128 ký tự.', 'error');
    if (password !== confirm) return setMessage(message, 'Mật khẩu nhập lại chưa khớp.', 'error');
    if (!terms) return setMessage(message, 'Cần đồng ý Điều khoản và Chính sách quyền riêng tư để tạo tài khoản.', 'error');

    const cfg = window.STOCKRADAR_AUTH_CONFIG || {};
    if (!cfg.configured || !cfg.supabaseUrl || !cfg.supabasePublishableKey) {
      return setMessage(message, 'Dịch vụ tạo tài khoản chưa sẵn sàng.', 'error');
    }

    setBusy(form, true, 'Đang tạo tài khoản…');
    setMessage(message, 'Đang tạo tài khoản và gửi liên kết xác minh email…');

    try {
      const response = await fetch(`${String(cfg.supabaseUrl).replace(/\/$/, '')}/functions/v1/signup-link`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          apikey: String(cfg.supabasePublishableKey),
        },
        body: JSON.stringify({
          email,
          password,
          plan,
          terms_accepted: true,
          privacy_accepted: true,
          terms_version: TERMS_VERSION,
          privacy_version: PRIVACY_VERSION,
          product_email_consent_version: CONSENT_VERSION,
          product_email_daily_brief: plan === 'premium' && Boolean(form.elements.email_daily_brief?.checked),
          product_email_event_alerts: plan === 'premium' && Boolean(form.elements.email_event_alerts?.checked),
        }),
        cache: 'no-store',
        credentials: 'omit',
      });

      let data = {};
      try { data = await response.json(); } catch (_) {}

      form.elements.password.value = '';
      form.elements.password_confirm.value = '';

      if (!response.ok || data?.ok !== true) {
        const text = response.status === 409
          ? 'Chưa thể tạo tài khoản mới. Nếu email này đã có tài khoản, hãy đăng nhập; nếu chưa, vui lòng thử lại.'
          : 'Chưa thể gửi email xác minh. Vui lòng thử lại sau.';
        return setMessage(message, text, 'error');
      }

      try {
        sessionStorage.setItem('sr_pending_signup_plan', plan);
        sessionStorage.setItem('sr_pending_signup_next', destinationFor(plan));
        sessionStorage.setItem('sr_pending_signup_email', email);
      } catch (_) {}
      showEmailSent(form, panel, email, plan);
    } catch (_) {
      form.elements.password.value = '';
      form.elements.password_confirm.value = '';
      setMessage(message, 'Không thể kết nối dịch vụ tạo tài khoản. Vui lòng thử lại.', 'error');
    } finally {
      setBusy(form, false);
    }
  }

  function init() {
    const form = document.querySelector('[data-auth-signup-form]');
    const panel = document.querySelector('[data-signup-email-sent]');
    if (!form || !panel) return;

    document.querySelector('[data-auth-signup-otp-form]')?.remove();
    syncExistingLogin(form);

    form.addEventListener('submit', event => submitSignup(event, form, panel), true);

    panel.querySelector('[data-signup-email-back]')?.addEventListener('click', () => {
      panel.hidden = true;
      form.hidden = false;
      form.elements.email?.focus();
    });

    form.querySelectorAll('input[name="selected_plan"]').forEach(input => {
      input.addEventListener('change', () => {
        syncExistingLogin(form);
        redirectExistingPremiumUser(form);
      });
    });

    const params = new URLSearchParams(location.search);
    if (params.get('plan') === 'premium') redirectExistingPremiumUser(form);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
