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
    readiness: null,
    accessRefreshed: false,
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
      const date = new Date(value);
      if (!Number.isFinite(date.getTime())) return '—';
      return new Intl.DateTimeFormat('vi-VN', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Ho_Chi_Minh',
      }).format(date);
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
    if (raw.includes('CHECKOUT_DISABLED')) return 'Premium tạm dừng kích hoạt mới. Bạn có thể đăng ký quan tâm; chưa chuyển khoản.';
    if (raw.includes('PLAN_NOT_AVAILABLE')) return 'Gói Premium hiện chưa mở bán.';
    if (raw.includes('CHECKOUT_EXPIRED')) return 'Mã thanh toán đã hết hạn. Hãy tạo lại yêu cầu thanh toán.';
    if (raw.includes('CHECKOUT_NOT_FOUND')) return 'Không tìm thấy yêu cầu thanh toán của tài khoản này.';
    return 'Chưa thể tạo yêu cầu thanh toán. Vui lòng thử lại.';
  }

  function getClient() {
    if (runtime.client) return runtime.client;
    const cfg = config();
    if (!cfg.configured || !window.supabase?.createClient) return null;
    runtime.client = window.StockRadarAuthClient || window.supabase.createClient(
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
    window.StockRadarAuthClient = runtime.client;
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

  function firstText(object, keys) {
    for (const key of keys) {
      const value = object?.[key];
      if (value === null || value === undefined) continue;
      const text = String(value).trim();
      if (text) return text;
    }
    return '';
  }

  function checkoutReference(request) {
    return firstText(request, [
      'payment_reference', 'paymentReference', 'transfer_content', 'transferContent',
      'transfer_reference', 'transferReference', 'reference', 'payment_code', 'paymentCode', 'code',
    ]).toUpperCase();
  }

  function checkoutExpiry(request) {
    const direct = firstText(request, [
      'expires_at', 'expiresAt', 'valid_until', 'validUntil', 'expiry_at', 'expiryAt', 'expiry', 'expires',
    ]);
    if (direct && Number.isFinite(new Date(direct).getTime())) return direct;
    const created = firstText(request, ['created_at', 'createdAt', 'issued_at', 'issuedAt']);
    if (created) {
      const createdAt = new Date(created).getTime();
      if (Number.isFinite(createdAt)) return new Date(createdAt + 30 * 60 * 1000).toISOString();
    }
    return '';
  }

  function qrUrl(request) {
    const reference = checkoutReference(request);
    if (!reference) return '';
    const bankBin = request?.bank_bin || request?.bankBin;
    const accountNumber = request?.account_number || request?.accountNumber;
    const accountName = request?.account_name || request?.accountName;
    if (!runtime.readiness?.checkout_ready || !bankBin || !accountNumber || !accountName) return '';
    const base = `https://img.vietqr.io/image/${encodeURIComponent(bankBin)}-${encodeURIComponent(accountNumber)}-compact2.png`;
    const params = new URLSearchParams({
      amount: String(request?.amount_vnd || request?.amount || runtime.amount),
      addInfo: reference,
      accountName,
    });
    return `${base}?${params.toString()}`;
  }

  function renderQr(request) {
    const image = document.querySelector('[data-checkout-qr-image]');
    const placeholder = document.querySelector('[data-checkout-qr-placeholder]');
    const url = qrUrl(request);
    const reference = checkoutReference(request);
    if (image) {
      image.hidden = !url;
      if (url) image.src = url; else image.removeAttribute('src');
      image.alt = url ? `VietQR thanh toán ${reference}` : '';
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
      if (!Number.isFinite(remaining)) return;
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
    const reference = checkoutReference(request || {});
    const expiresAt = checkoutExpiry(request || {});
    const requestId = firstText(request, ['request_id', 'requestId', 'checkout_id', 'checkoutId']);
    const checkoutFlag = request?.checkout_enabled ?? request?.checkoutEnabled;
    const enabled = Boolean(runtime.readiness?.checkout_ready === true && requestId && checkoutFlag === true);
    const amount = Number(request?.amount_vnd || request?.amount || runtime.amount);
    const status = firstText(request, ['status']).toUpperCase();
    const normalized = request ? {
      ...request,
      request_id: requestId || request.request_id,
      payment_reference: reference || request.payment_reference,
      expires_at: expiresAt || request.expires_at,
      status: status || request.status,
      checkout_enabled: enabled,
    } : null;

    runtime.request = normalized;
    document.querySelectorAll('[data-checkout-payment]').forEach(node => { node.hidden = !enabled; });
    runtime.amount = amount;
    runtime.durationDays = Number(request?.duration_days || request?.durationDays || 30);

    setText('[data-checkout-amount]', formatVnd(amount));
    setText('[data-checkout-bank]', request?.bank_name || request?.bankName || '—');
    setText('[data-checkout-account-number]', request?.account_number || request?.accountNumber || '—');
    setText('[data-checkout-account-name]', request?.account_name || request?.accountName || '—');
    setText('[data-checkout-reference]', reference || '—');
    setText('[data-checkout-expiry-at]', expiresAt ? formatDateTime(expiresAt) : (reference ? 'Mã có thời hạn tối đa 30 phút' : '—'));
    setCopyValue('[data-copy-account]', request?.account_number || request?.accountNumber);
    setCopyValue('[data-copy-reference]', reference);
    renderQr(enabled ? normalized : null);
    if (expiresAt) startCountdown(expiresAt);
    else {
      stopCountdown();
      setText('[data-checkout-expiry]', reference ? 'Tối đa 30 phút từ lúc tạo mã' : '—');
    }

    const confirm = document.querySelector('[data-checkout-confirm]');
    if (confirm) {
      const confirmable = enabled && status === 'PENDING';
      confirm.disabled = !confirmable;
      confirm.textContent = status === 'USER_CONFIRMED'
        ? 'Đã ghi nhận · Chờ đối soát'
        : status === 'PAID'
          ? 'Premium đã được kích hoạt'
          : 'Tôi đã chuyển khoản · Gửi xác nhận';
    }

    showPaymentFallback(!runtime.readiness?.checkout_ready);

    if (!enabled && status !== 'PAID' && status !== 'USER_CONFIRMED') return;
    if (status === 'PENDING') {
      setState(`Mã thanh toán ${reference} đã được cấp riêng cho tài khoản này. Sau khi chuyển khoản, bấm xác nhận để StockRadar gửi yêu cầu duyệt tới email quản trị.`, 'ok');
    } else if (status === 'USER_CONFIRMED') {
      setState('Yêu cầu đã được ghi nhận và đang chờ đối soát. Premium chỉ kích hoạt sau khi thanh toán được xác minh.', 'warn');
    } else if (status === 'PAID') {
      setState(`Thanh toán đã được xác minh. Premium đang hoạt động${request?.paid_until ? ` đến ${formatDateTime(request.paid_until)}` : ''}.`, 'ok');
      stopPolling();
      stopCountdown();
      if (!runtime.accessRefreshed) {
        runtime.accessRefreshed = true;
        getClient().rpc('get_my_stockradar_access').then(({data,error}) => {
          if (!error && data?.account_tier === 'PAID') window.dispatchEvent(new CustomEvent('stockradar-access-changed'));
        });
      }
      const mobile = document.querySelector('[data-checkout-mobile-action]');
      if (mobile) {
        mobile.textContent = 'Mở tài khoản Premium';
        mobile.href = 'tai-khoan/?premium=active';
      }
    } else if (status === 'EXPIRED') {
      setState('Mã thanh toán đã hết hạn. Tải lại trang để tạo yêu cầu mới.', 'warn');
      stopPolling();
      stopCountdown();
    }
  }

  async function loadReadiness() {
    let data = null;
    try { const result = await getClient()?.rpc('get_stockradar_product_readiness_v1'); if (!result?.error) data = result?.data; } catch (_) {}
    runtime.readiness = data?.schema_version === 'STOCKRADAR_PRODUCT_READINESS_V1' ? data : null;
    const ready = runtime.readiness?.checkout_ready === true;
    document.body.dataset.checkoutReady = String(ready);
    if (!ready) {
      document.querySelectorAll('[data-checkout-payment]').forEach(node => { node.hidden = true; });
      document.querySelector('[data-checkout-qr-image]')?.removeAttribute('src');
      setCopyValue('[data-copy-account]', ''); setCopyValue('[data-copy-reference]', '');
      const confirm = document.querySelector('[data-checkout-confirm]'); if (confirm) confirm.disabled = true;
      setState(data ? 'Premium tạm dừng kích hoạt mới: dữ liệu, email hoặc thanh toán chưa đủ điều kiện.' : 'Chưa xác minh được trạng thái Premium. Vui lòng thử lại; chưa chuyển khoản.', 'warn');
      document.querySelectorAll('[data-checkout-login],[data-checkout-mobile-action]').forEach(node => {
        node.textContent = 'Đăng ký quan tâm Premium'; node.href = 'dang-ky/#premium';
      });
    }
    showPaymentFallback(!ready);
    return ready;
  }

  async function loadRequest() {
    const client = getClient();
    if (!client || !runtime.user) return null;
    if (!await loadReadiness()) throw new Error('CHECKOUT_DISABLED');
    const { data, error } = await client.rpc('create_my_checkout_request', { p_plan_code: 'ADVANCED_TEST' });
    if (error) throw error;
    renderRequest(data);
    if(data?.request_id && data?.checkout_enabled===true)window.StockRadarAnalytics?.checkoutCreated();
    return data;
  }

  async function refreshRequest() {
    const client = getClient();
    const id = runtime.request?.request_id;
    if (!client || !id) return;
    await loadReadiness();
    const { data, error } = await client.rpc('get_my_checkout_request', { p_checkout_id: id });
    if (error) return;
    renderRequest({ ...runtime.request, ...data });
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
    if (!await loadReadiness()) { renderRequest(runtime.request); return; }
    button.disabled = true;
    button.textContent = 'Đang gửi xác nhận…';
    try {
      const { data, error } = await client.rpc('confirm_my_checkout_request', { p_checkout_id: id });
      if (error) throw error;
      renderRequest({ ...runtime.request, ...data });
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
    const ready = await loadReadiness();
    if (!ready) { renderRequest(null); return; }
    if (!runtime.user) {
      if (login) {
        login.textContent = 'Đăng nhập để tạo mã thanh toán';
        login.href = `dang-nhap/?next=${encodeURIComponent('thanh-toan/?plan=premium')}`;
      }
      if (mobile) {
        mobile.textContent = 'Đăng nhập để tạo mã thanh toán';
        mobile.href = `dang-nhap/?next=${encodeURIComponent('thanh-toan/?plan=premium')}`;
      }
      setState('Thanh toán đã đủ điều kiện. Đăng nhập để nhận mã chuyển khoản riêng và VietQR.', 'warn');
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
