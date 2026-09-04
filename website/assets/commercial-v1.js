(() => {
  'use strict';

  function siteUrl(path) {
    return new URL(String(path || '').replace(/^\/+/, ''), document.baseURI).toString();
  }

  function normalizeCommercialChrome() {
    document.querySelectorAll('.header-register-cta').forEach(link => {
      link.href = siteUrl('dang-ky/?plan=free');
      link.textContent = 'Bắt đầu miễn phí';
      link.setAttribute('aria-label', 'Bắt đầu với StockRadar Free');
    });

    document.querySelectorAll('.conversion-mobile-cta,.mobile-newsletter-bar').forEach(node => node.remove());
  }

  function mount() {
    normalizeCommercialChrome();
    setTimeout(normalizeCommercialChrome, 50);
    setTimeout(normalizeCommercialChrome, 500);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
