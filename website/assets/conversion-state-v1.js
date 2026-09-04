(() => {
  'use strict';

  const LEAD_CAPTURED_KEY = 'sr_email_lead_captured';

  function captured() {
    try { return localStorage.getItem(LEAD_CAPTURED_KEY) === '1'; } catch (_) { return false; }
  }

  function emailDeliveryReady() {
    return window.STOCKRADAR_AUTH_CONFIG?.emailDeliveryReady === true;
  }

  function siteUrl(path) {
    return new URL(String(path || '').replace(/^\/+/, ''), document.baseURI).toString();
  }

  function apply() {
    if (!captured()) return;
    const ready = emailDeliveryReady();
    const href = siteUrl(ready ? 'signup/?plan=free' : 'dang-ky/');
    const label = ready ? 'Hoàn tất Free' : 'Xem gói';

    document.querySelectorAll('.header-register-cta').forEach(link => {
      link.href = href;
      link.textContent = label;
      link.setAttribute('aria-label', ready
        ? 'Hoàn tất tài khoản Free để kích hoạt bản rà soát 09:00'
        : 'Xem gói Free và Premium của StockRadar');
    });

    document.querySelectorAll('[data-conversion-free-lead]').forEach(link => {
      link.href = href;
      link.textContent = ready ? 'Hoàn tất tài khoản Free' : 'Xem gói Free / Premium';
    });

    document.querySelectorAll('[data-conversion-mobile-lead]').forEach(link => {
      link.href = href;
      link.textContent = ready ? 'Hoàn tất Free' : 'Xem gói';
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', apply, { once: true });
  else apply();
})();
