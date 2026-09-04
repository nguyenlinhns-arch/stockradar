(() => {
  'use strict';

  function validTicker(value) {
    const ticker = String(value || '').trim().toUpperCase();
    return ticker.length === 3 && /^[A-Z0-9]{3}$/.test(ticker) && /[A-Z]/.test(ticker) ? ticker : '';
  }

  function tickerFromLocation() {
    const pathParts = location.pathname.split('/').filter(Boolean);
    const routeTicker = pathParts[pathParts.length - 1] !== 'co-phieu' ? pathParts[pathParts.length - 1] : '';
    return validTicker(new URLSearchParams(location.search).get('ticker') || routeTicker);
  }

  function addWidget(slot, src, config) {
    if (!slot || slot.dataset.mounted === 'true') return;
    slot.dataset.mounted = 'true';
    slot.innerHTML = '<div class="public-market-loading">Đang tải dữ liệu thị trường…</div>';

    const container = document.createElement('div');
    container.className = 'tradingview-widget-container';
    container.style.height = '100%';
    container.style.width = '100%';
    const widget = document.createElement('div');
    widget.className = 'tradingview-widget-container__widget';
    widget.style.height = '100%';
    widget.style.width = '100%';
    container.appendChild(widget);
    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = src;
    script.async = true;
    script.textContent = JSON.stringify(config);
    container.appendChild(script);
    slot.replaceChildren(container);
  }

  function mount() {
    const ticker = tickerFromLocation();
    const freeCard = document.querySelector('.analysis-tier-free');
    const freeContent = freeCard?.querySelector('[data-dynamic-stock-report]');
    if (!ticker || !freeCard || !freeContent || freeContent.querySelector('[data-public-market-reference]')) return;

    const section = document.createElement('section');
    section.className = 'public-market-reference';
    section.dataset.publicMarketReference = '';
    section.innerHTML = `
      <header class="public-market-reference-head">
        <div>
          <span class="panel-label">DỮ LIỆU THỊ TRƯỜNG · HOSE:${ticker}</span>
          <h3>${ticker} · Giá hiện tại & biểu đồ</h3>
          <p>Xem dữ liệu thị trường trực tiếp trước. Phần kết luận StockRadar được tách riêng phía dưới và chỉ xuất hiện khi Decision Feed đạt chuẩn.</p>
        </div>
        <span class="public-market-reference-badge">LIVE REFERENCE</span>
      </header>
      <div class="public-market-widget public-market-symbol" data-tv-symbol-info aria-label="Thông tin giá ${ticker}"></div>
      <div class="public-market-widget public-market-chart" data-tv-chart aria-label="Biểu đồ ${ticker}"></div>
      <details class="public-market-more">
        <summary>Xem hồ sơ doanh nghiệp & dữ liệu tài chính</summary>
        <div class="public-market-reference-grid">
          <div class="public-market-widget public-market-profile" data-tv-profile aria-label="Hồ sơ doanh nghiệp ${ticker}"></div>
          <div class="public-market-widget public-market-financials" data-tv-financials aria-label="Dữ liệu tài chính ${ticker}"></div>
        </div>
      </details>
      <p class="public-market-reference-note">Dữ liệu tham chiếu được hiển thị trực tiếp bằng TradingView widget. StockRadar không dùng tín hiệu/điểm của TradingView làm tín hiệu mua bán.</p>`;

    // Live market data must be the first thing users see in the Free result.
    freeContent.prepend(section);
    const symbol = `HOSE:${ticker}`;

    addWidget(section.querySelector('[data-tv-symbol-info]'), 'https://s3.tradingview.com/external-embedding/embed-widget-symbol-info.js', {
      symbol,
      width: '100%',
      locale: 'vi_VN',
      colorTheme: 'light',
      isTransparent: true
    });

    addWidget(section.querySelector('[data-tv-chart]'), 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js', {
      autosize: true,
      symbol,
      interval: 'D',
      timezone: 'Asia/Ho_Chi_Minh',
      theme: 'light',
      style: '1',
      locale: 'vi_VN',
      allow_symbol_change: false,
      calendar: false,
      support_host: 'https://www.tradingview.com'
    });

    const details = section.querySelector('.public-market-more');
    details?.addEventListener('toggle', () => {
      if (!details.open) return;
      addWidget(section.querySelector('[data-tv-profile]'), 'https://s3.tradingview.com/external-embedding/embed-widget-symbol-profile.js', {
        width: '100%',
        height: '100%',
        colorTheme: 'light',
        isTransparent: true,
        symbol,
        locale: 'vi_VN'
      });
      addWidget(section.querySelector('[data-tv-financials]'), 'https://s3.tradingview.com/external-embedding/embed-widget-financials.js', {
        colorTheme: 'light',
        isTransparent: true,
        largeChartUrl: '',
        displayMode: 'adaptive',
        width: '100%',
        height: '100%',
        symbol,
        locale: 'vi_VN'
      });
    }, { passive: true });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
