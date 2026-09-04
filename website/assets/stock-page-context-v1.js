(() => {
  'use strict';

  function validTicker(value) {
    const ticker = String(value || '').trim().toUpperCase();
    return ticker.length === 3
      && /^[A-Z0-9]{3}$/.test(ticker)
      && /[A-Z]/.test(ticker)
      ? ticker
      : '';
  }

  function tickerFromLocation() {
    const parts = location.pathname.split('/').filter(Boolean);
    const routeTicker = parts[parts.length - 1] !== 'co-phieu' ? parts[parts.length - 1] : '';
    const raw = new URLSearchParams(location.search).get('ticker') || routeTicker;
    return validTicker(raw);
  }

  function mount() {
    const ticker = tickerFromLocation();
    if (!ticker) return;
    const heading = document.querySelector('.page-heading h1');
    const intro = document.querySelector('.stock-analysis-intro');
    const freeTitle = document.getElementById('free-analysis-title');
    const premiumTitle = document.getElementById('premium-analysis-title');
    if (heading) heading.textContent = `Phân tích ${ticker}`;
    if (intro) intro.textContent = `So sánh trực tiếp bản Free và lớp Premium cho ${ticker} theo bốn khung đầu tư.`;
    if (freeTitle) freeTitle.textContent = `Free · ${ticker}`;
    if (premiumTitle) premiumTitle.textContent = `Premium · ${ticker}`;
    document.title = `${ticker} — Phân tích Free & Premium | StockRadar`;
  }

  document.addEventListener('DOMContentLoaded', mount, { once: true });
})();
