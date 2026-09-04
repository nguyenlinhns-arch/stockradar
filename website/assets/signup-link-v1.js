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

  function destinationFor(plan) {
    return new URL(plan === 'premium' ? 'thanh-toan/?plan=premium' : 'tai-khoan/', document.baseURI).toString();
  }

  function syncExistingLogin(form) {
    const link = document.querySelector('[data-signup-existing-login]');
    if (!link) return;
    const next = selectedPlan(form) === 'premium' ? 'thanh-toan/?plan=premium' : 'tai-khoan/';
    link.href = `dang-nhap/?next=${encodeURIComponent(next)}`;
  }

  function authClient() {
    const cfg = window.STOCKRADAR_AUTH_CONFIG || {};
    if (!cfg.configured || !cfg.supabaseUrl || !cfg.supabasePublishableKey || !window.supabase?.createClient) return null;
    return window.supabase.createClient(
      String(cfg.supabaseUrl).replace(/\/$/, ''),
      String(cfg.supabasePublishableKey),
      { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, storageKey: 'stockradar-auth' } },
    );
  }

  async function redirectExistingPremiumUser(form) {
    if (selectedPlan(form) !== 'premium') return false;
    const client = authClient();
    if (!client) return false;
    try {
      const { data } = await client.auth.getUser();
      if (data?.user) {
        window.location.replace(destinationFor('premium'));
        return true;
      }
    } catch (_) {}
    return false;
  }

  async function signInCreatedAccount(client, email, password) {
    let lastError = null;
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const { data, error } = await client.auth.signInWithPassword({ email, password });
      if (!error && data?.session) return data;
      lastError = error || new Error('missing session');
      if (attempt < 2) await new Promise(resolve => setTimeout(resolve, 300 * (attempt + 1)));
    }
    throw lastError || new Error('sign in failed');
  }

  async function submitSignup(event, form) {
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
    const client = authClient();
    if (!client || !cfg.supabaseUrl || !cfg.supabasePublishableKey) {
      return setMessage(message, 'Dịch vụ tạo tài khoản chưa sẵn sàng.', 'error');
    }

    setBusy(form, true, 'Đang tạo tài khoản…');
    setMessage(message, 'Đang tạo tài khoản…');

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

      if (!response.ok || data?.ok !== true) {
        form.elements.password.value = '';
        form.elements.password_confirm.value = '';
        const text = response.status === 409
          ? 'Không thể tạo tài khoản mới. Nếu email này đã có tài khoản, hãy đăng nhập.'
          : 'Chưa thể tạo tài khoản. Vui lòng thử lại sau.';
        return setMessage(message, text, 'error');
      }

      setMessage(message, plan === 'premium'
        ? 'Tạo tài khoản thành công. Đang mở thanh toán Premium…'
        : 'Tạo tài khoản thành công. Đang mở tài khoản Free…', 'success');

      await signInCreatedAccount(client, email, password);
      form.elements.password.value = '';
      form.elements.password_confirm.value = '';
      window.location.replace(destinationFor(plan));
    } catch (_) {
      form.elements.password.value = '';
      form.elements.password_confirm.value = '';
      setMessage(message, 'Tài khoản có thể đã được tạo nhưng chưa thể tự đăng nhập. Hãy dùng nút Đăng nhập bên dưới.', 'error');
    } finally {
      setBusy(form, false);
    }
  }

  function init() {
    const form = document.querySelector('[data-auth-signup-form]');
    if (!form) return;

    document.querySelector('[data-auth-signup-otp-form]')?.remove();
    document.querySelector('[data-signup-email-sent]')?.remove();
    syncExistingLogin(form);

    form.addEventListener('submit', event => submitSignup(event, form), true);

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
