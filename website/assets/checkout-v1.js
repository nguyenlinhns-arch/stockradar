(() => {
  'use strict';

  const runtime = {
    amount: 199000,
    durationDays: 30,
    plan: 'StockRadar Premium',
    user: null,
    request: null,
    client: null,
    pollTimer: null,
    countdownTimer: null,
  };

  function config() {
    return window.STOCKRADAR_AUTH_CONFIG || {};
  }

  function formatVnd(value) {
    return new Intl.NumberFormat('vi-VN').format(Number(value || 0)) + 'đ';
  }

  function formatDateTime(value) {
    if (!value) return '—';
    try {
      return new Intl.DateTimeFormat('vi-VN', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit', hour12: false,
      }).format(new Date(value));
    } catch (_) {
      return '—';
    }
  }

  function siteUrl(path = '') {
    return new URL(String(path).replace(/^\/+/, ''), document.baseURI).toString();
  }

  function setText(selector, value) {
    document.querySelectorAll(selector).forEach(node => { node.textContent = value; });
  }

  function setState(message, kind = 'warn') {
    document.querySelectorAll('[data-checkout-state]').forEach(node => {
      node.className = `checkout-state is-${kind}`;
      node.textContent = message;
    });
  }

  function checkoutError(error) {
    const raw = String(error?.message || error || '').toUpperCase();
    if (raw.includes('AUTH_REQUIRED')) return 'Vui lòng đăng nhập trước khi thanh toán.';
    if (raw.includes('EMAIL_VERIFICATION_REQUIRED')) return 'Hãy xác minh email tài khoản trước khi thanh toán.';
    if (raw.includes('ACCOUNT_NOT_ACTIVE')) return 'Tài khoản chưa ở trạng thái hoạt động.';
    if (raw.includes('CHECKOUT_DISABLED')) return 'StockRadar đã hoàn thiện luồng thanh toán nhưng tài khoản nhận tiền chưa được kích hoạt.';
    if (raw.includes('PLAN_NOT_AVAILABLE')) return 'Gói Premium hiện chưa mở bán.';
    if (raw.includes('CHECKOUT_EXPIRED')) return 'Mã thanh toán đã hết hạn. Hãy tạo lại yêu cầu thanh toán.';
    if (raw.includes('CHECKOUT_NOT_FOUND')) return 'Không tìm thấy yêu cầu thanh toán của tài khoản này.';
    return 'Chưa thể tạo yêu cầu thanh toán. Vui lòng thử lại.';
  }

  function getClient() {
    if (runtime.client) return runtime.client;
    const cfg = config();
    if (!cfg.configured || !window.supabase?.createClient) return null;
    runtime.client = window.supabase.createClient(
      String(cfg.supabaseUrl || '').replace(/\/+$/, ''),
      String(cfg.supabasePublishableKey || ''),
      {
        auth: {
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true,
          storageKey: 'stockradar-auth',
        },
      }
    );
    window.StockRadarCheckoutClient = runtime.client;
    return runtime.client;
  }

  async function currentUser() {
    const client = getClient();
    if (!client) return null;
    const { data, error } = await client.auth.getUser();
    if (error) return null;
    return data?.user || null;
  }

  async function copyValue(value, button) {
    if (!value || !button) return;
    try {
      await navigator.clipboard.writeText(value);
      const old = button.textContent;
      button.textContent = 'Đã chép';
      setTimeout(() => { button.textContent = old; }, 1400);
    } catch (_) {}
  }

  function wireCopyButtons() {
    document.querySelectorAll('[data-copy-value]').forEach(button => {
      button.addEventListener('click', () => copyValue(button.dataset.copyValue || '', button));
    });
  }

  function setCopyValue(selector, value) {
    document.querySelectorAll(selector).forEach(button => {
      button.dataset.copyValue = value || '';
      button.disabled = !value;
    });
  }

  function qrUrl(request) {
    if (!request?.bank_bin || !request?.account_number || !request?.payment_reference) return '';
    const base = `https://img.vietqr.io/image/${encodeURIComponent(request.bank_bin)}-${encodeURIComponent(request.account_number)}-compact2.png`;
    const params = new URLSearchParams({
      amount: String(request.amount_vnd || runtime.amount),
      addInfo: request.payment_reference,
      accountName: request.account_name || '',
    });
    return `${base}?${params.toString()}`;
  }

  function renderQr(request) {
    const image = document.querySelector('[data-checkout-qr-image]');
    const placeholder = document.querySelector('[data-checkout-qr-placeholder]');
    const url = qrUrl(request);
    if (image) {
      image.hidden = !url;
      image.src = url || '';
      image.alt = url ? `VietQR thanh toán ${request.payment_reference}` : '';
    }
    if (placeholder) placeholder.hidden = Boolean(url);
  }

  function stopCountdown() {
    if (runtime.countdownTimer) clearInterval(runtime.countdownTimer);
    runtime.countdownTimer = null;
  }

  function startCountdown(expiresAt) {
    stopCountdown();
    const target = document.querySelector('[data-checkout-expiry]');
    if (!target || !expiresAt) return;
    const render = () => {
      const remaining = new Date(expiresAt).getTime() - Date.now();
      if (remaining <= 0) {
        target.textContent = 'Đã hết hạn';
        stopCountdown();
        return;
      }
      const minutes = Math.floor(remaining / 60000);
      const seconds = Math.floor((remaining % 60000) / 1000);
      target.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    };
    render();
    runtime.countdownTimer = setInterval(render, 1000);
  }

  function showPaymentFallback(show) {
    document.querySelectorAll('[data-checkout-disabled-fallback]').forEach(node => { node.hidden = !show; });
  }

  function renderRequest(request) {
    runtime.request = request || null;
    const enabled = Boolean(request?.checkout_enabled && request?.request_id);
    const amount = Number(request?.amount_vnd || runtime.amount);
    runtime.amount = amount;
    runtime.durationDays = Number(request?.duration_days || 30);

    setText('[data-checkout-amount]', formatVnd(amount));
    setText('[data-checkout-bank]', enabled ? (request.bank_name || '—') : 'Chưa mở');
    setText('[data-checkout-account-number]', enabled ? (request.account_number || '—') : '—');
    setText('[data-checkout-account-name]', enabled ? (request.account_name || '—') : '—');
    setText('[data-checkout-reference]', enabled ? (request.payment_reference || '—') : '—');
    setText('[data-checkout-expiry-at]', enabled ? formatDateTime(request.expires_at) : '—');
    setCopyValue('[data-copy-account]', enabled ? request.account_number : '');
    setCopyValue('[data-copy-reference]', enabled ? request.payment_reference : '');
    renderQr(enabled ? request : null);
    startCountdown(enabled ? request.expires_at : null);

    const confirm = document.querySelector('[data-checkout-confirm]');
    if (confirm) {
      const confirmable = enabled && request.status === 'PENDING';
      confirm.disabled = !confirmable;
      confirm.textContent = request?.status === 'USER_CONFIRMED'
        ? 'Đã gửi xác nhận · Đang chờ đối soát'
        : request?.status === 'PAID'
          ? 'Premium đã được kích hoạt'
          : 'Tôi đã chuyển khoản · Gửi xác nhận';
    }

    showPaymentFallback(!enabled);

    if (!enabled) return;
    if (request.status === 'PENDING') {
      setState(`Mã thanh toán ${request.payment_reference} đã được cấp riêng cho tài khoản này. Chuyển đúng số tiền và nội dung trước khi mã hết hạn.`, 'ok');
    } else if (request.status === 'USER_CONFIRMED') {
      setState('Đã nhận xác nhận chuyển khoản. StockRadar đang chờ đối soát trước khi kích hoạt Premium.', 'warn');
    } else if (request.status === 'PAID') {
      setState(`Thanh toán đã được xác minh. Premium đang hoạt động${request.paid_until ? ` đến ${formatDateTime(request.paid_until)}` : ''}.`, 'ok');
      stopPolling();
      stopCountdown();
      const mobile = document.querySelector('[data-checkout-mobile-action]');
      if (mobile) {
        mobile.textContent = 'Mở tài khoản Premium';
        mobile.href = 'tai-khoan/?premium=active';
      }
    } else if (request.status === 'EXPIRED') {
      setState('Mã thanh toán đã hết hạn. Tải lại trang để tạo yêu cầu mới.', 'warn');
      stopPolling();
      stopCountdown();
    }
  }

  async function loadRequest() {
    const client = getClient();
    if (!client || !runtime.user) return null;
    const { data, error } = await client.rpc('create_my_checkout_request', { p_plan_code: 'ADVANCED_TEST' });
    if (error) throw error;
    renderRequest(data);
    return data;
  }

  async function refreshRequest() {
    const client = getClient();
    const id = runtime.request?.request_id;
    if (!client || !id) return;
    const { data, error } = await client.rpc('get_my_checkout_request', { p_checkout_id: id });
    if (error) return;
    renderRequest({ ...runtime.request, ...data, checkout_enabled: true });
  }

  function stopPolling() {
    if (runtime.pollTimer) clearInterval(runtime.pollTimer);
    runtime.pollTimer = null;
  }

  function startPolling() {
    stopPolling();
    if (!runtime.request?.request_id || runtime.request?.status === 'PAID') return;
    runtime.pollTimer = setInterval(refreshRequest, 8000);
  }

  async function confirmTransfer() {
    const client = getClient();
    const button = document.querySelector('[data-checkout-confirm]');
    const id = runtime.request?.request_id;
    if (!client || !id || !button) return;
    button.disabled = true;
    button.textContent = 'Đang gửi xác nhận…';
    try {
      const { data, error } = await client.rpc('confirm_my_checkout_request', { p_checkout_id: id });
      if (error) throw error;
      renderRequest({ ...runtime.request, ...data, checkout_enabled: true });
      startPolling();
    } catch (error) {
      button.disabled = false;
      button.textContent = 'Tôi đã chuyển khoản · Gửi xác nhận';
      setState(checkoutError(error), 'warn');
    }
  }

  function wireConfirm() {
    document.querySelector('[data-checkout-confirm]')?.addEventListener('click', confirmTransfer);
  }

  async function renderAccount() {
    runtime.user = await currentUser();
    const target = document.querySelector('[data-checkout-account-email]');
    const login = document.querySelector('[data-checkout-login]');
    const mobile = document.querySelector('[data-checkout-mobile-action]');

    if (target) target.textContent = runtime.user?.email || 'Chưa đăng nhập';
    if (!runtime.user) {
      if (login) {
        login.textContent = 'Đăng nhập để thanh toán';
        login.href = `dang-nhap/?next=${encodeURIComponent('thanh-toan/?plan=premium')}`;
      }
      if (mobile) {
        mobile.textContent = 'Đăng nhập để thanh toán';
        mobile.href = `dang-nhap/?next=${encodeURIComponent('thanh-toan/?plan=premium')}`;
      }
      setState('Đăng nhập bằng tài khoản đã xác minh để tạo mã thanh toán riêng.', 'warn');
      showPaymentFallback(false);
      return;
    }

    if (login) {
      login.textContent = 'Quản lý tài khoản';
      login.href = 'tai-khoan/';
    }
    if (mobile) {
      mobile.textContent = 'Tạo mã thanh toán';
      mobile.href = '#payment';
    }

    try {
      await loadRequest();
      startPolling();
    } catch (error) {
      renderRequest(null);
      setState(checkoutError(error), 'warn');
    }
  }

  async function mount() {
    setText('[data-checkout-amount]', formatVnd(runtime.amount));
    wireCopyButtons();
    wireConfirm();
    await renderAccount();
  }

  window.addEventListener('pagehide', () => {
    stopPolling();
    stopCountdown();
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
