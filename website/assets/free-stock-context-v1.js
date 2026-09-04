(() => {
  'use strict';

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
    }[character]));
  }

  function validTicker(value) {
    const ticker = String(value || '').trim().toUpperCase();
    return ticker.length === 3
      && /^[A-Z0-9]{3}$/.test(ticker)
      && /[A-Z]/.test(ticker)
      ? ticker
      : '';
  }

  function tickerFromLocation() {
    const pathParts = location.pathname.split('/').filter(Boolean);
    const routeTicker = pathParts[pathParts.length - 1] !== 'co-phieu' ? pathParts[pathParts.length - 1] : '';
    const raw = new URLSearchParams(location.search).get('ticker') || routeTicker;
    return validTicker(raw);
  }

  function loadMarketReferenceAssets() {
    if (!document.querySelector('link[data-market-reference-style]')) {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.dataset.marketReferenceStyle = '';
      link.href = new URL('assets/public-market-reference-v1.css?v=20260904-market3', document.baseURI).toString();
      document.head.appendChild(link);
    }
    if (!document.querySelector('script[data-market-reference-script]')) {
      const script = document.createElement('script');
      script.src = new URL('assets/public-market-reference-v1.js?v=20260904-market4', document.baseURI).toString();
      script.async = true;
      script.dataset.marketReferenceScript = '';
      document.head.appendChild(script);
    }
  }

  let universePromise;
  function loadUniverse() {
    if (!universePromise) {
      universePromise = fetch(new URL('public/data/ticker-universe.json', document.baseURI), { cache: 'no-store' })
        .then(response => response.ok ? response.json() : { items: [] })
        .catch(() => ({ items: [] }));
    }
    return universePromise;
  }

  function fullPublicReportPresent(target) {
    return Boolean(target.querySelector('.position-detail-grid, .ticker-history, .evidence-grid'));
  }

  function clearFallback(target) {
    target.querySelector('[data-free-stock-context]')?.remove();
    target.classList.remove('has-free-context');
  }

  function markup(ticker, security) {
    const verified = Boolean(security);
    const identity = verified
      ? [security.company_name, security.sector].filter(Boolean).join(' · ')
      : 'Decision Feed StockRadar chưa phát hành';
    return `
      <section class="free-context-card free-context-card-compact" data-free-stock-context>
        <div class="free-context-compact-row">
          <div>
            <span class="panel-label">KẾT LUẬN STOCKRADAR</span>
            <strong>${escapeHtml(ticker)} · CHƯA PHÁT HÀNH MUA/BÁN</strong>
            <small>${escapeHtml(identity)}. Dữ liệu thị trường thực tế được hiển thị ở phía trên; StockRadar chỉ bổ sung Score, xếp hạng, 4 khung, Fair Value và kế hoạch hành động khi Decision Feed đạt chuẩn.</small>
          </div>
          <span class="free-context-status ${verified ? 'is-verified' : ''}">DECISION PENDING</span>
        </div>
      </section>`;
  }

  async function enhance(target) {
    if (!target) return;
    if (fullPublicReportPresent(target)) {
      clearFallback(target);
      return;
    }
    if (target.querySelector('[data-free-stock-context]')) return;
    if (!target.querySelector('.data-readiness, .ticker-accepted, .lookup-quick-result')) return;
    const ticker = tickerFromLocation();
    if (!ticker) return;
    const payload = await loadUniverse();
    if (fullPublicReportPresent(target)) {
      clearFallback(target);
      return;
    }
    if (target.querySelector('[data-free-stock-context]')) return;
    const security = Array.isArray(payload.items) ? payload.items.find(item => item.ticker === ticker) : null;
    target.insertAdjacentHTML('beforeend', markup(ticker, security));
    target.classList.add('has-free-context');
  }

  function mount() {
    loadMarketReferenceAssets();
    const target = document.querySelector('[data-dynamic-stock-report]');
    if (!target) return;
    const run = () => enhance(target);
    run();
    new MutationObserver(run).observe(target, { childList: true, subtree: true });
  }

  document.addEventListener('DOMContentLoaded', mount, { once: true });
})();
