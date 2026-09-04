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

  function shouldLoadAI() {
    const parts = location.pathname.split('/').filter(Boolean).map(part => part.toLowerCase());
    const excluded = new Set(['signup', 'dang-ky', 'dang-nhap', 'dat-lai-mat-khau', 'tai-khoan', 'dieu-khoan', 'quyen-rieng-tu', 'email']);
    return !parts.some(part => excluded.has(part));
  }

  function loadStockRadarAI() {
    if (!shouldLoadAI() || document.querySelector('script[data-stockradar-ai-loader]')) return;
    if (!document.querySelector('link[data-stockradar-ai-style]')) {
      const css = document.createElement('link');
      css.rel = 'stylesheet';
      css.href = siteUrl('assets/ai-assistant.css?v=20260904-ai1');
      css.dataset.stockradarAiStyle = '';
      document.head.append(css);
    }
    const script = document.createElement('script');
    script.src = siteUrl('assets/ai-assistant.js?v=20260904-ai1');
    script.async = true;
    script.dataset.stockradarAiLoader = '';
    document.head.append(script);
  }

  function apply() {
    loadStockRadarAI();
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
