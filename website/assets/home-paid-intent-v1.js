(() => {
  'use strict';

  const TICKER_KEY = 'sr_conversion_ticker_v1';

  function normalizeTicker(value) {
    const ticker = String(value || '').trim().toUpperCase();
    return /^[A-Z0-9]{3}$/.test(ticker) ? ticker : '';
  }

  function setTicker(ticker) {
    const value = normalizeTicker(ticker);
    if (!value) return;
    document.querySelectorAll('[data-home-intent-ticker]').forEach((node) => {
      node.textContent = value;
    });
    document.querySelectorAll('[data-premium-conversion-cta]').forEach((link) => {
      const href = link.getAttribute('href');
      if (!href) return;
      try {
        const url = new URL(href, document.baseURI);
        url.searchParams.set('ticker', value);
        link.setAttribute('href', url.pathname.replace(/^\//, '') + url.search + url.hash);
      } catch (_) {}
    });
  }

  function rememberedTicker() {
    try { return normalizeTicker(sessionStorage.getItem(TICKER_KEY)); } catch (_) { return ''; }
  }

  document.querySelectorAll('[data-stock-search-form]').forEach((form) => {
    const input = form.querySelector('input[name="ticker"]');
    input?.addEventListener('input', () => {
      const ticker = normalizeTicker(input.value);
      if (ticker) setTicker(ticker);
    });
    form.addEventListener('submit', () => {
      const ticker = normalizeTicker(input?.value);
      if (ticker) setTicker(ticker);
    });
  });

  const params = new URLSearchParams(window.location.search);
  setTicker(normalizeTicker(params.get('ticker')) || rememberedTicker());
})();
