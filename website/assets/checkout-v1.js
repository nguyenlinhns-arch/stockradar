(() => {
  'use strict';

  const config = window.STOCKRADAR_AUTH_CONFIG || {};
  const checkout = {
    enabled: false,
    amount: 199000,
    plan: 'StockRadar Premium',
    durationDays: 30,
    bankName: '',
    accountNumber: '',
    accountName: '',
    paymentReference: '',
  };

  function formatVnd(value) {
    return new Intl.NumberFormat('vi-VN').format(Number(value || 0)) + 'đ';
  }

  function setText(selector, value) {
    document.querySelectorAll(selector).forEach(node => { node.textContent = value; });
  }

  async function currentUser() {
    if (!config.configured || !window.supabase?.createClient) return null;
    const client = window.StockRadarCheckoutClient || window.supabase.createClient(
      config.supabaseUrl,
      config.supabasePublishableKey,
      {
        auth: {
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true,
          storageKey: 'stockradar-auth',
        },
      }
    );
    window.StockRadarCheckoutClient = client;
    const { data, error } = await client.auth.getUser();
    if (error) return null;
    return data?.user || null;
  }

  function copyValue(value, button) {
    if (!value || !navigator.clipboard) return;
    navigator.clipboard.writeText(value).then(() => {
      const old = button.textContent;
      button.textContent = 'Đã chép';
      setTimeout(() => { button.textContent = old; }, 1400);
    }).catch(() => {});
  }

  function mountCopyButtons() {
    document.querySelectorAll('[data-copy-value]').forEach(button => {
      const value = button.dataset.copyValue || '';
      button.disabled = !value;
      button.addEventListener('click', () => copyValue(value, button));
    });
  }

  function renderPaymentDetails() {
    setText('[data-checkout-amount]', formatVnd(checkout.amount));
    setText('[data-checkout-bank]', checkout.bankName || 'Sẽ hiển thị khi mở thanh toán');
    setText('[data-checkout-account-number]', checkout.accountNumber || '—');
    setText('[data-checkout-account-name]', checkout.accountName || '—');
    setText('[data-checkout-reference]', checkout.paymentReference || 'Sẽ cấp riêng cho từng giao dịch');

    document.querySelectorAll('[data-copy-account]').forEach(button => {
      button.dataset.copyValue = checkout.accountNumber;
    });
    document.querySelectorAll('[data-copy-reference]').forEach(button => {
      button.dataset.copyValue = checkout.paymentReference;
    });

    const confirm = document.querySelector('[data-checkout-confirm]');
    const state = document.querySelector('[data-checkout-state]');
    if (confirm) confirm.disabled = !checkout.enabled;
    if (state) {
      state.className = `checkout-state ${checkout.enabled ? 'is-ok' : 'is-warn'}`;
      state.textContent = checkout.enabled
        ? 'Thanh toán đang mở. Sau khi hệ thống xác minh giao dịch, Premium được kích hoạt 30 ngày.'
        : 'Trang thanh toán đã sẵn sàng về giao diện. Cổng thanh toán hiện chưa mở nên StockRadar chưa hiển thị tài khoản nhận tiền hoặc mã giao dịch.';
    }
  }

  async function renderAccount() {
    const user = await currentUser();
    const target = document.querySelector('[data-checkout-account-email]');
    const login = document.querySelector('[data-checkout-login]');
    const mobile = document.querySelector('[data-checkout-mobile-action]');

    if (target) target.textContent = user?.email || 'Chưa đăng nhập';
    if (login) {
      login.textContent = user ? 'Quản lý tài khoản' : 'Đăng nhập để thanh toán';
      login.href = user ? 'tai-khoan/' : `dang-nhap/?next=${encodeURIComponent('thanh-toan/?plan=premium')}`;
    }
    if (mobile) {
      mobile.textContent = user ? 'Tiếp tục thanh toán' : 'Đăng nhập để thanh toán';
      mobile.href = user ? '#payment' : `dang-nhap/?next=${encodeURIComponent('thanh-toan/?plan=premium')}`;
    }
  }

  function mountConfirm() {
    const button = document.querySelector('[data-checkout-confirm]');
    const state = document.querySelector('[data-checkout-state]');
    if (!button) return;
    button.addEventListener('click', () => {
      if (!checkout.enabled) return;
      button.disabled = true;
      if (state) {
        state.className = 'checkout-state is-warn';
        state.textContent = 'Đã ghi nhận yêu cầu xác nhận. Hệ thống đang chờ đối soát giao dịch trước khi kích hoạt Premium.';
      }
    });
  }

  async function mount() {
    renderPaymentDetails();
    mountCopyButtons();
    mountConfirm();
    await renderAccount();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
