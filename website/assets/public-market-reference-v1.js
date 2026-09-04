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
    if (!ticker || !freeCard || freeCard.querySelector('[data-public-market-reference]')) return;

    const section = document.createElement('section');
    section.className = 'public-market-reference';
    section.dataset.publicMarketReference = '';
    section.innerHTML = `
      <header class="public-market-reference-head">
        <div>
          <span class="panel-label">DỮ LIỆU THỊ TRƯỜNG HIỂN THỊ TRỰC TIẾP</span>
          <h3>${ticker} · Giá, biểu đồ và dữ liệu doanh nghiệp</h3>
          <p>Hiển thị trực tiếp bởi TradingView cho <strong>HOSE:${ticker}</strong>. Lớp này giúp Free có dữ liệu tham chiếu ngay; StockRadar không tải xuống, xử lý hay dùng dữ liệu TradingView làm đầu vào cho Radar/khuyến nghị.</p>
        </div>
        <span class="public-market-reference-badge">THAM CHIẾU</span>
      </header>
      <div class="public-market-widget public-market-symbol" data-tv-symbol-info aria-label="Thông tin giá ${ticker}"></div>
      <div class="public-market-widget public-market-chart" data-tv-chart aria-label="Biểu đồ ${ticker}"></div>
      <div class="public-market-reference-grid">
        <div class="public-market-widget public-market-profile" data-tv-profile aria-label="Hồ sơ doanh nghiệp ${ticker}"></div>
        <div class="public-market-widget public-market-financials" data-tv-financials aria-label="Dữ liệu tài chính ${ticker}"></div>
      </div>
      <p class="public-market-reference-note">Nguồn hiển thị tham chiếu: TradingView widget. Trạng thái MUA/CHỜ, Buy Zone, Stop, Target và R:R của StockRadar chỉ xuất hiện khi feed StockRadar vượt Data Gate riêng.</p>`;

    freeCard.appendChild(section);
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
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
