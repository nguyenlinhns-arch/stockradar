(() => {
  'use strict';

  function normalize(value) {
    return String(value || '').trim().toUpperCase();
  }

  function valid(ticker) {
    return /^(?=.*[A-Z])[A-Z0-9]{3}$/.test(ticker);
  }

  function analysisUrl(ticker) {
    return new URL(`co-phieu/?ticker=${encodeURIComponent(ticker)}`, document.baseURI).href;
  }

  function navigate(ticker) {
    const normalized = normalize(ticker);
    if (!valid(normalized)) return;
    const target = analysisUrl(normalized);
    if (window.location.href === target) return;
    window.location.assign(target);
  }

  // Keep the existing search handler alive for validation/analytics, then move directly
  // to the two-column analysis page in the same interaction.
  document.addEventListener('submit', event => {
    const form = event.target.closest?.('[data-stock-search-form]');
    if (!form) return;
    const ticker = normalize(form.querySelector('input[name="ticker"]')?.value);
    if (!valid(ticker)) return;
    setTimeout(() => navigate(ticker), 0);
  }, true);

  // Autocomplete selection should also be one interaction, not select -> open.
  document.addEventListener('click', event => {
    const option = event.target.closest?.('[data-ticker-value]');
    if (!option) return;
    const ticker = normalize(option.dataset.tickerValue);
    if (!valid(ticker)) return;
    setTimeout(() => navigate(ticker), 0);
  }, true);

  // Deep links to the lookup page with ?ticker=XYZ should resolve to analysis immediately.
  document.addEventListener('DOMContentLoaded', () => {
    const route = window.location.pathname.replace(/\/+$/, '');
    if (!/(?:\/kiem-tra-co-phieu|\/phan-tich)$/.test(route)) return;
    const ticker = normalize(new URLSearchParams(window.location.search).get('ticker'));
    if (valid(ticker)) setTimeout(() => navigate(ticker), 0);
  }, { once: true });
})();
