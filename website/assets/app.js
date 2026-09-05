(() => {
  const apiMode = document.documentElement.dataset.apiMode || 'auto';
  const allowedEvents = new Set([
    'ad_click', 'landing_view', 'radar_view', 'top5_expand', 'track_record_view',
    'signup_started', 'signup_completed', 'alert_opt_in', 'pro_page_view',
    'trial_started', 'subscription_started', 'return_d1', 'return_d7',
    'horizon_select', 'stock_search',
    'stock_report_view', 'top10_view', 'watchlist_add', 'email_view',
    'checkout_started', 'payment_completed',
    'top_view', 'horizon_change', 'sector_view', 'recommendation_list_view',
    'performance_view', 'sample_premium_report_view', 'signup_start',
    'signup_complete', 'pro_view', 'checkout_start', 'payment_complete',
    'email_open', 'email_click', 'renewal_complete'
    , 'ticker_search', 'four_horizon_view', 'holding_view', 'recommendation_public_view'
    , 'recommendation_history_view', 'today_changes_view', 'benchmark_view'
    , 'onboarding_horizon_selected', 'onboarding_sector_selected', 'onboarding_ticker_added'
    , 'paid_email_preference_changed', 'ticker_input_started', 'ticker_autocomplete_selected'
    , 'ticker_search_submitted', 'ticker_search_valid', 'ticker_search_invalid'
    , 'ticker_cache_hit', 'ticker_cache_miss', 'quick_report_view', 'full_report_requested'
    , 'report_generation_completed', 'report_generation_failed', 'ticker_trial_cta_clicked'
    , 'ticker_watch_started'
  ]);

  const stateLabels = {
    WATCH: 'THEO DÕI',
    NEAR_TRIGGER: 'CHỜ MUA',
    READY: 'ĐẠT VÙNG MUA',
    TRIGGERED: 'ĐANG CÓ HIỆU LỰC',
    WAIT_BUY: 'CHỜ MUA',
    IN_BUY_ZONE: 'ĐẠT VÙNG MUA',
    ACTIVE: 'ĐANG CÓ HIỆU LỰC',
    INVALIDATED: 'KHÔNG CÒN ĐẠT ĐIỀU KIỆN',
    EXTENDED: 'TĂNG QUÁ VÙNG MUA',
    TARGET_REACHED: 'ĐẠT MỤC TIÊU',
    STOP_REACHED: 'CHẠM MỨC CẮT LỖ',
    EXPIRED: 'HẾT THỜI HẠN',
    CLOSED: 'ĐÓNG KHUYẾN NGHỊ',
    UNACTIVATED: 'CHƯA KÍCH HOẠT',
    ACTIVATED: 'ĐÃ KÍCH HOẠT',
    UNCHANGED: 'KHÔNG ĐỔI'
  };

  const horizonLabels = {
    SHORT_TERM: 'NGẮN HẠN',
    MEDIUM_TERM: 'TRUNG HẠN',
    LONG_TERM: 'DÀI HẠN',
    ACCUMULATION: 'TÍCH SẢN'
  };

  const marketLabels = {
    GREEN: 'XANH · THUẬN LỢI',
    YELLOW: 'VÀNG · THẬN TRỌNG',
    RED: 'ĐỎ · PHÒNG THỦ'
  };

  function stateLabel(value) {
    return stateLabels[value] || String(value || '—').replaceAll('_', ' ');
  }

  function marketLabel(value) {
    return marketLabels[value] || String(value || '—').replaceAll('_', ' ');
  }

  function statusLabel(value) {
    if (value === 'SHORTLIST_FROM_AVAILABLE_DATA') return 'DATA GATE';
    return String(value || '—').replaceAll('_', ' ');
  }

  function formatSnapshot(value) {
    if (!value) return '—';
    return new Intl.DateTimeFormat('vi-VN', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: false
    }).format(new Date(value));
  }

  function formatPrice(value) {
    return value == null ? '—' : Number(value).toLocaleString('vi-VN', { maximumFractionDigits: 2 });
  }

  function formatDate(value) {
    if (!value) return '—';
    return new Intl.DateTimeFormat('vi-VN', {
      day: '2-digit', month: '2-digit', year: 'numeric'
    }).format(new Date(value));
  }

  function formatPercent(value, signed = true) {
    if (value == null) return '—';
    const number = Number(value);
    return `${signed && number > 0 ? '+' : ''}${number.toLocaleString('vi-VN', {
      minimumFractionDigits: 2, maximumFractionDigits: 2
    })}%`;
  }

  function returnClass(value) {
    if (value == null || Number(value) === 0) return 'return-flat';
    return Number(value) > 0 ? 'return-positive' : 'return-negative';
  }

  function lifecycleGroup(item) {
    if (!item.activation_timestamp || item.recommendation_state === 'UNACTIVATED') return 'UNACTIVATED';
    if (item.status === 'CLOSED' || item.close_timestamp) return 'CLOSED';
    return 'OPEN';
  }

  function performanceValue(item) {
    const group = lifecycleGroup(item);
    if (group === 'UNACTIVATED') return { label: 'CHƯA KÍCH HOẠT', value: null, group };
    if (group === 'CLOSED') return { label: formatPercent(item.final_return_pct), value: item.final_return_pct, group };
    return { label: formatPercent(item.current_return_pct), value: item.current_return_pct, group };
  }

  function priceRange(low, high) {
    if (low == null || high == null) return '—';
    return `${formatPrice(low)}–${formatPrice(high)}`;
  }

  function mountPortalShell() {
    if (document.querySelector('[data-verified-recommendations], [data-live-research-radar]')) return;
    const header = document.querySelector('.site-header');
    if (!header || document.querySelector('.portal-utility')) return;

    const menu = header.querySelector('[data-nav-menu]');
    if (menu) {
      const route = location.pathname.replace(/\/+$/, '');
      const items = [
        ['radar5/', 'Radar', '/radar5'],
        ['kiem-tra-co-phieu/', 'Tra cứu mã', '/kiem-tra-co-phieu'],
        ['khuyen-nghi/', 'Khuyến nghị', '/khuyen-nghi'],
        ['thay-doi-hom-nay/', 'Thay đổi', '/thay-doi-hom-nay'],
        ['hieu-qua/', 'Hiệu quả', '/hieu-qua'],
        ['nganh/', 'Theo ngành', '/nganh'],
      ];
      menu.innerHTML = items.map(([href, label, match]) => {
        const isCurrent = route.endsWith(match)
          || route.includes(`${match}/`)
          || (match === '/kiem-tra-co-phieu' && (route.includes('/co-phieu/') || route.includes('/phan-tich')));
        return `<a href="${href}"${isCurrent ? ' aria-current="page"' : ''}>${label}</a>`;
      }).join('');
    }

    const utility = document.createElement('div');
    utility.className = 'portal-utility';
    utility.innerHTML = `
      <div class="container portal-utility-inner">
        <span><strong>STOCKRADAR.VN</strong><i></i>HOSE</span>
        <span class="portal-utility-note">HOSE · Tra mã vận hành · Giá/OHLCV đang chờ nguồn được cấp quyền</span>
      </div>`;

    const tape = document.createElement('section');
    tape.className = 'market-tape';
    tape.setAttribute('aria-label', 'Trạng thái dữ liệu StockRadar');
    tape.innerHTML = `
      <div class="container market-tape-inner" aria-live="polite">
        <div class="tape-heading"><span class="live-dot" aria-hidden="true"></span><span>DỮ LIỆU</span><strong>GATE</strong></div>
        <div class="tape-item"><span>Trạng thái</span><strong data-market>ĐANG KIỂM TRA</strong></div>
        <div class="tape-item"><span>Hồ sơ nội bộ</span><strong data-reference-count>—</strong></div>
        <div class="tape-item tape-snapshot"><span>Cập nhật</span><strong data-reference-snapshot>—</strong></div>
        <div class="tape-disclaimer">Giá/OHLCV chưa kết nối</div>
      </div>`;

    const subnav = document.createElement('nav');
    subnav.className = 'product-subnav';
    subnav.setAttribute('aria-label', 'Điều hướng nhanh');
    subnav.innerHTML = `<div class="container product-subnav-inner">
      <a href="radar5/">Radar</a><a href="breakout/">Điểm mua</a><a href="risk/">Cảnh báo</a>
      <a href="khuyen-nghi/">Đang hiệu lực</a><a href="thay-doi-hom-nay/">Thay đổi hôm nay</a>
      <a href="track-record/">Lịch sử</a><a href="nganh/">Theo ngành</a><a href="hieu-qua/">Hiệu quả</a>
    </div>`;

    const footer = document.querySelector('.site-footer');
    if (footer) {
      const links = footer.querySelector('.footer-links');
      if (links) links.innerHTML = '<a href="radar5/">Radar</a><a href="kiem-tra-co-phieu/">Tra cứu</a><a href="khuyen-nghi/">Khuyến nghị</a><a href="hieu-qua/">Hiệu quả</a>';
      const disclaimer = footer.querySelector('.disclaimer');
      if (disclaimer) disclaimer.textContent = 'Kết quả chỉ được phát hành khi dữ liệu thị trường và quyền sử dụng đã vượt qua Data Gate.';
    }

    header.before(utility);
    header.after(tape);
    tape.after(subnav);
  }

  function siteUrl(path) {
    return new URL(String(path).replace(/^\/+/, ''), document.baseURI).toString();
  }

  function apiUrl(path) {
    if (apiMode === 'disabled') return null;
    const configuredBase = document.documentElement.dataset.apiBase;
    return new URL(String(path).replace(/^\/+/, ''), configuredBase || document.baseURI).toString();
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"]/g, character => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'
    }[character]));
  }

  let tickerAssetsPromise;
  function loadTickerAssets() {
    if (!tickerAssetsPromise) {
      tickerAssetsPromise = Promise.all([
        fetch(siteUrl('public/data/ticker-universe.json'), { cache: 'no-store' }).then(response => {
          if (!response.ok) throw new Error('Không tải được ticker master');
          return response.json();
        }),
        fetch(siteUrl('public/data/stock-reports.json'), { cache: 'no-store' }).then(response => {
          if (!response.ok) throw new Error('Không tải được lớp báo cáo');
          return response.json();
        })
      ]).then(([master, reports]) => ({
        master,
        reports,
        securityByTicker: new Map(master.items.map(item => [item.ticker, item])),
        reportByTicker: new Map(reports.items.map(item => [item.ticker, item]))
      }));
    }
    return tickerAssetsPromise;
  }

  function internalReference(master = {}) {
    return master.internal_reference || {};
  }

  function publicPayloadBlocked(data) {
    const status = String(data?.data_status || data?.status || '');
    return !data || !status || status.startsWith('BLOCKED');
  }

  function publicMarketDataReady(data) {
    return Boolean(!publicPayloadBlocked(data) && data.snapshot?.data_grade === 'DECISION_GRADE');
  }

  function licensedReportReady(report) {
    const status = String(report?.data_status || 'INSUFFICIENT');
    return Boolean(report && !status.startsWith('BLOCKED') && status !== 'INSUFFICIENT');
  }

  function dataReadinessMarkup(master = {}, surface = 'DỮ LIỆU THỊ TRƯỜNG', compact = false) {
    const reference = internalReference(master);
    const validated = Number(reference.validated_count || 0);
    const total = Number(reference.record_count || 0);
    const coverage = total ? `${validated}/${total}` : '—';
    return `<section class="data-readiness ${compact ? 'is-compact' : ''}">
      <header><div><span class="panel-label">DATA GATE</span><h2>${escapeHtml(surface)}</h2></div><span class="data-pill">CHỜ NGUỒN ĐƯỢC CẤP QUYỀN</span></header>
      <div class="readiness-grid">
        <div><span>Hồ sơ tham chiếu nội bộ</span><strong>${coverage}</strong></div>
        <div><span>Tra mã</span><strong>SẴN SÀNG</strong></div>
        <div><span>Giá &amp; OHLCV</span><strong>CHƯA KẾT NỐI</strong></div>
        <div><span>Xếp hạng toàn HOSE</span><strong>ĐANG KHÓA</strong></div>
      </div>
    </section>`;
  }

  function tickerAcceptedMarkup(ticker, master = {}, compact = false) {
    const reference = internalReference(master);
    const count = Number(reference.record_count || 0);
    return `<div class="ticker-accepted ${compact ? 'is-compact' : ''}">
      <header><div><span class="panel-label">ĐÃ NHẬN MÃ</span><h2>${escapeHtml(ticker)}</h2></div><span class="data-pill">CHỜ XÁC MINH DỮ LIỆU</span></header>
      <div class="accepted-metrics"><div><span>Định dạng</span><strong>HỢP LỆ</strong></div><div><span>Hồ sơ nội bộ</span><strong>${count ? `${count} BẢN GHI` : '—'}</strong></div><div><span>Giá</span><strong>—</strong></div><div><span>Kết luận</span><strong>—</strong></div></div>
    </div>`;
  }

  async function loadDataReadiness() {
    const targets = document.querySelectorAll('[data-data-readiness], [data-reference-count], [data-reference-snapshot], [data-feed-status], [data-ranking-status]');
    if (!targets.length) return;
    try {
      const { master } = await loadTickerAssets();
      const reference = internalReference(master);
      document.querySelectorAll('[data-data-readiness]').forEach(target => {
        target.innerHTML = dataReadinessMarkup(master, target.dataset.dataReadiness || 'NỀN DỮ LIỆU', target.dataset.compact === 'true');
      });
      document.querySelectorAll('[data-reference-count]').forEach(target => {
        target.textContent = reference.record_count ? `${reference.validated_count}/${reference.record_count}` : '—';
      });
      document.querySelectorAll('[data-reference-snapshot]').forEach(target => { target.textContent = formatSnapshot(reference.as_of); });
      document.querySelectorAll('[data-feed-status]').forEach(target => { target.textContent = reference.market_data_ready ? 'SẴN SÀNG' : 'CHƯA KẾT NỐI'; });
      document.querySelectorAll('[data-ranking-status]').forEach(target => { target.textContent = reference.ranking_ready ? 'SẴN SÀNG' : 'ĐANG KHÓA'; });
    } catch (error) {
      document.querySelectorAll('[data-data-readiness]').forEach(target => { target.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`; });
    }
  }

  function recentTickers() {
    try {
      return JSON.parse(localStorage.getItem('sr_recent_tickers') || '[]').filter(isValidStockTicker).slice(0, 8);
    } catch (_) {
      return [];
    }
  }

  function renderRecentTickers() {
    const items = recentTickers();
    document.querySelectorAll('[data-recent-tickers]').forEach(target => {
      target.innerHTML = items.length
        ? items.map(ticker => `<a href="co-phieu/?ticker=${encodeURIComponent(ticker)}">${escapeHtml(ticker)}</a>`).join('')
        : '<span>Chưa có mã đã tra.</span>';
    });
  }

  function rememberTicker(ticker) {
    if (!isValidStockTicker(ticker)) return;
    const items = [ticker, ...recentTickers().filter(item => item !== ticker)].slice(0, 8);
    localStorage.setItem('sr_recent_tickers', JSON.stringify(items));
    renderRecentTickers();
  }

  function sessionId() {
    let value = localStorage.getItem('sr_session_id');
    if (!value) {
      value = crypto.randomUUID ? crypto.randomUUID() : `sr-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      localStorage.setItem('sr_session_id', value);
    }
    return value;
  }

  function getUtm() {
    const params = new URLSearchParams(location.search);
    const keys = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'proposition'];
    const current = {};
    keys.forEach(key => {
      const value = params.get(key);
      if (value) current[key] = value.slice(0, 120);
    });
    if (Object.keys(current).length) localStorage.setItem('sr_utm', JSON.stringify(current));
    try { return JSON.parse(localStorage.getItem('sr_utm') || '{}'); } catch (_) { return {}; }
  }

  function track(name, properties = {}) {
    if (!allowedEvents.has(name)) return;
    const payload = {
      event_name: name,
      occurred_at: new Date().toISOString(),
      session_id: sessionId(),
      page: location.pathname,
      proposition: document.body.dataset.proposition || getUtm().proposition || 'organic',
      utm: getUtm(),
      properties
    };
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ event: name, ...payload });
    const endpoint = apiUrl('api/events');
    if (!endpoint) return;
    const body = JSON.stringify(payload);
    if (navigator.sendBeacon) {
      navigator.sendBeacon(endpoint, new Blob([body], { type: 'application/json' }));
    } else {
      fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body, keepalive: true }).catch(() => {});
    }
  }

  function retentionEvents() {
    const now = Date.now();
    const first = Number(localStorage.getItem('sr_first_seen') || now);
    if (!localStorage.getItem('sr_first_seen')) localStorage.setItem('sr_first_seen', String(now));
    const days = (now - first) / 86400000;
    if (days >= 1 && !localStorage.getItem('sr_return_d1')) {
      localStorage.setItem('sr_return_d1', '1'); track('return_d1');
    }
    if (days >= 7 && !localStorage.getItem('sr_return_d7')) {
      localStorage.setItem('sr_return_d7', '1'); track('return_d7');
    }
  }

  function stateClass(state) {
    return `state-${String(state).toLowerCase().replaceAll('_', '-')}`;
  }

  function renderMiniRadar(target, data) {
    if (!target) return;
    target.innerHTML = data.items.map(item => `
      <div class="radar-row">
        <span class="rank">${item.rank}</span>
        <div><div class="ticker">${item.ticker}</div><div class="setup">${item.setup}</div></div>
        <div class="radar-row-status"><div class="score">${item.score}</div><span class="state ${stateClass(item.state)}">${stateLabel(item.state)}</span></div>
      </div>`).join('');
  }

  function renderRadarTable(target, data, filter = 'ALL') {
    if (!target) return;
    const items = data.items.filter(item => filter === 'ALL' || item.state === filter);
    target.innerHTML = `
      <div class="table-row table-head"><span>Hạng</span><span>Mã / thiết lập</span><span>Điểm</span><span>Trạng thái</span><span>Giá</span><span>Cách pivot</span><span>Thay đổi</span></div>
      ${items.map(item => `
        <article class="table-row" data-ticker="${item.ticker}">
          <strong class="rank">#${item.rank}</strong>
          <div><a class="table-ticker ticker-link" href="co-phieu/?ticker=${encodeURIComponent(item.ticker)}">${item.ticker}</a><div class="setup">${item.setup} · ${item.reason}</div></div>
          <strong class="score">${item.score}</strong>
          <span><span class="state ${stateClass(item.state)}">${stateLabel(item.state)}</span></span>
          <span class="market-price">${Number(item.current_price).toLocaleString('vi-VN')}</span>
          <span class="pivot-distance">${Number(item.distance_to_pivot_pct).toLocaleString('vi-VN')}%</span>
          <span class="change ${item.state_change === 'UNCHANGED' ? 'unchanged' : ''}">${item.state_change === 'UNCHANGED' ? stateLabel(item.state_change) : item.state_change.split('→').map(stateLabel).join(' → ')}</span>
        </article>`).join('') || '<div class="empty">Không có mã ở trạng thái này.</div>'}`;
  }

  function recommendationLink(item) {
    return `<a class="table-ticker ticker-link" href="co-phieu/?ticker=${encodeURIComponent(item.ticker)}">${item.ticker}</a>`;
  }

  function renderRecommendations(target, data, filter = 'ALL') {
    const items = data.items.filter(item => filter === 'ALL' || lifecycleGroup(item) === filter);
    target.innerHTML = `
      <div class="rec-row rec-head"><span>Mã</span><span>Kỳ hạn</span><span>Công bố</span><span>Kích hoạt</span><span>Vùng mua</span><span>Entry hiệu quả</span><span>Giá hiện tại / đóng</span><span>Lãi / lỗ</span><span>Mục tiêu</span><span>Rủi ro</span><span>Review due</span><span>Review</span><span>Trạng thái</span></div>
      ${items.map(item => {
        const performance = performanceValue(item);
        const displayPrice = performance.group === 'CLOSED' ? item.close_price : item.current_price;
        return `
          <article class="rec-row" data-lifecycle="${performance.group}">
            <div>${recommendationLink(item)}<small>${item.sector}</small></div>
            <strong>${horizonLabels[item.horizon] || item.horizon}</strong>
            <span>${formatDate(item.publication_date)}<small>${item.publication_time || ''}</small></span>
            <span>${item.activation_timestamp ? formatSnapshot(item.activation_timestamp) : '—'}<small>${item.activation_timestamp ? 'Lần chạm đầu tiên' : 'Chưa vào vùng'}</small></span>
            <span>${priceRange(item.recommended_buy_low, item.recommended_buy_high)}</span>
            <span>${formatPrice(item.performance_entry_price)}</span>
            <span>${formatPrice(displayPrice)}<small>${performance.group === 'CLOSED' ? 'Giá đóng đã khóa' : 'Quan sát mới'}</small></span>
            <strong class="performance-cell ${returnClass(performance.value)}">${performance.label}</strong>
            <span>${formatPrice(item.target_price)}</span>
            <span>${item.stop_loss == null ? 'Theo luận điểm' : formatPrice(item.stop_loss)}<small>${item.risk_level}</small></span>
            <span>${formatSnapshot(item.review_due_at)}</span>
            <span>${escapeHtml(item.review_status || 'PENDING')}<small>${escapeHtml(item.review_decision || 'Chưa có quyết định')}</small></span>
            <span><span class="state ${stateClass(item.recommendation_state)}">${stateLabel(item.recommendation_state)}</span></span>
          </article>`;
      }).join('') || '<div class="empty">Không có record trong nhóm này.</div>'}`;
  }

  function renderPerformance(target, data) {
    const summary = data.performance_summary;
    const horizons = Object.entries(horizonLabels).map(([key, label]) => {
      const records = data.items.filter(item => item.horizon === key);
      const closed = records.filter(item => lifecycleGroup(item) === 'CLOSED');
      const average = closed.length ? closed.reduce((total, item) => total + Number(item.final_return_pct || 0), 0) / closed.length : null;
      return `<div class="horizon-performance-row"><strong>${label}</strong><span>${records.length} công bố</span><span>${closed.length} đã đóng</span><b class="${returnClass(average)}">${average == null ? 'Chưa đủ mẫu' : formatPercent(average)}</b></div>`;
    }).join('');
    const rows = data.items.map(item => {
      const performance = performanceValue(item);
      const finalPrice = performance.group === 'CLOSED' ? item.close_price : item.current_price;
      return `<article class="performance-row">
        <div>${recommendationLink(item)}<small>${horizonLabels[item.horizon]}</small></div>
        <span>${formatDate(item.publication_date)}</span>
        <span>${item.activation_timestamp ? formatSnapshot(item.activation_timestamp) : 'Chưa kích hoạt'}</span>
        <span>${formatPrice(item.performance_entry_price)}</span>
        <span>${formatPrice(finalPrice)}</span>
        <strong class="${returnClass(performance.value)}">${performance.label}</strong>
        <span>${formatPercent(item.benchmark_return_pct)}<small>${item.vnindex_at_activation == null ? 'Chưa đủ dữ liệu' : `VN-Index ${formatPrice(item.vnindex_at_activation)} → ${formatPrice(item.vnindex_current_or_close)}`}</small></span>
        <strong class="${returnClass(item.excess_return_pct)}">${formatPercent(item.excess_return_pct)}</strong>
        <span><span class="state ${stateClass(item.recommendation_state)}">${stateLabel(item.recommendation_state)}</span></span>
      </article>`;
    }).join('');
    target.innerHTML = `
      <section class="performance-summary-grid" aria-label="Tóm tắt hiệu quả">
        <article><span>Tổng công bố</span><strong>${summary.total_published}</strong><small>Bản ghi</small></article>
        <article><span>Chưa kích hoạt</span><strong>${summary.unactivated}</strong><small>Không tính lãi/lỗ</small></article>
        <article><span>Đang mở</span><strong>${summary.open}</strong><small>Mark-to-market</small></article>
        <article><span>Đã đóng</span><strong>${summary.closed}</strong><small>Kết quả đã khóa</small></article>
        <article><span>Tỷ lệ thắng</span><strong>${formatPercent(summary.win_rate_pct, false)}</strong><small>Chỉ record đã đóng</small></article>
        <article><span>Lợi nhuận đóng TB</span><strong class="${returnClass(summary.average_closed_return_pct)}">${formatPercent(summary.average_closed_return_pct)}</strong></article>
      </section>
      <section class="performance-breakdown"><header><div><span class="panel-label">THEO CHÂN TRỜI</span><h2>Theo mục tiêu</h2></div></header>${horizons}</section>
      <section class="performance-table"><div class="performance-row performance-head"><span>Mã</span><span>Công bố</span><span>Kích hoạt</span><span>Entry</span><span>Hiện tại / đóng</span><span>Lãi / lỗ</span><span>Benchmark</span><span>Vượt chuẩn</span><span>Trạng thái</span></div>${rows}</section>`;
  }

  function renderPerformanceMini(target, data) {
    const summary = data.performance_summary;
    target.innerHTML = `
      <div class="home-proof-stats"><div><span>Công bố</span><strong>${summary.total_published}</strong></div><div><span>Chưa kích hoạt</span><strong>${summary.unactivated}</strong></div><div><span>Đã đóng</span><strong>${summary.closed}</strong></div><div><span>Tỷ lệ thắng*</span><strong>${formatPercent(summary.win_rate_pct, false)}</strong></div></div>
      <div class="home-proof-list">${data.items.slice(0, 3).map(item => {
        const performance = performanceValue(item);
        return `<a href="co-phieu/?ticker=${encodeURIComponent(item.ticker)}"><span><strong>${item.ticker}</strong><small>${horizonLabels[item.horizon]}</small></span><span class="state ${stateClass(item.recommendation_state)}">${stateLabel(item.recommendation_state)}</span><b class="${returnClass(performance.value)}">${performance.label}</b></a>`;
      }).join('')}</div>
      <small class="home-proof-note">Dữ liệu đã vượt Data Gate</small>`;
  }

  function renderStockReport(target, item, data, stockReport = null) {
    const views = new Map((stockReport?.horizon_views || []).map(view => [view.horizon, view]));
    const horizonTabs = Object.entries(horizonLabels).map(([value, label]) => {
      const view = views.get(value);
      return `
      <div class="report-horizon ${value === item.horizon ? 'is-active' : ''}">
        <strong>${label}</strong><span>${escapeHtml(view?.assessment || (value === item.horizon ? 'Trạng thái hiện tại' : 'Chưa đủ dữ liệu'))}</span>
        <small>${view?.evaluated_at ? formatSnapshot(view.evaluated_at) : 'Chưa đánh giá'}</small>
      </div>`;
    }).join('');
    const list = values => (values || []).map(value => `<li>${value}</li>`).join('');
    const performance = performanceValue(item);
    target.innerHTML = `
      <section class="report-overview">
        <div class="report-title"><div><span class="panel-label">BÁO CÁO CỔ PHIẾU</span><h1>${item.ticker}</h1><p>${item.company_name} · ${item.sector}</p></div><span class="state ${stateClass(item.recommendation_state)}">${stateLabel(item.recommendation_state)}</span></div>
        <div class="report-metrics">
          <div><span>Giá hiện tại</span><strong>${formatPrice(item.current_price)}</strong></div>
          <div><span>Điểm nghiên cứu</span><strong>${formatPrice(item.stock_score)}<small>/100 · không phải xác suất</small></strong></div>
          <div><span>Xếp hạng mục tiêu</span><strong>#${item.rank}</strong></div>
          <div><span>Trạng thái thị trường</span><strong>${marketLabel(item.market_regime)}</strong></div>
          <div><span>P/L theo record</span><strong class="${returnClass(performance.value)}">${performance.label}</strong></div>
          <div><span>Cấp / chế độ</span><strong>${item.data_grade} · ${item.record_mode}</strong></div>
        </div>
      </section>
      <div class="report-horizons">${horizonTabs}</div>
      <section class="recommendation-plan">
        <header><div><span class="panel-label">KẾ HOẠCH CÓ ĐIỀU KIỆN</span><h2>${horizonLabels[item.horizon]}</h2></div><span class="data-pill">RESEARCH_ONLY</span></header>
        <div class="plan-metrics">
          <div><span>Ngày / giờ công bố</span><strong>${formatDate(item.publication_date)} · ${item.publication_time}</strong></div>
          <div><span>Giá lúc công bố</span><strong>${formatPrice(item.price_at_publication)}</strong></div>
          <div><span>Vùng mua đã khóa</span><strong>${priceRange(item.recommended_buy_low, item.recommended_buy_high)}</strong></div>
          <div><span>Thời điểm kích hoạt</span><strong>${item.activation_timestamp ? formatSnapshot(item.activation_timestamp) : 'CHƯA KÍCH HOẠT'}</strong></div>
          <div><span>Entry tính hiệu quả</span><strong>${formatPrice(item.performance_entry_price)}</strong></div>
          <div><span>Giá hiện tại / giá đóng</span><strong>${formatPrice(performance.group === 'CLOSED' ? item.close_price : item.current_price)}</strong></div>
          <div><span>Mục tiêu / giá trị hợp lý</span><strong>${formatPrice(item.target_price)}</strong></div>
          <div><span>Cắt lỗ / điểm vô hiệu</span><strong>${item.stop_loss == null ? 'Theo luận điểm' : formatPrice(item.stop_loss)}</strong></div>
          <div><span>Tỷ lệ lợi nhuận/rủi ro</span><strong>${item.risk_reward == null ? 'Không áp dụng máy móc' : `${formatPrice(item.risk_reward)}:1`}</strong></div>
          <div><span>Đánh giá lại chậm nhất</span><strong>${formatSnapshot(item.review_due_at)}</strong></div>
          <div><span>Trạng thái review</span><strong>${item.review_status || 'PENDING'}</strong></div>
        </div>
      </section>
      <section class="position-detail-grid">
        <article><span>MUA MỚI</span><h2>${escapeHtml(item.new_position_state)}</h2><p>${escapeHtml(item.new_position_note)}</p></article>
        <article><span>ĐANG NẮM GIỮ</span><h2>${escapeHtml(item.holding_state)}</h2><p>${escapeHtml(item.holding_note)}</p></article>
      </section>
      <section class="evidence-grid">
        <article><span class="panel-label">LUẬN ĐIỂM</span><ul>${list(item.thesis)}</ul></article>
        <article><span class="panel-label">RỦI RO / VÔ HIỆU</span><ul>${list([...(item.risks || []), ...(item.invalidation_conditions || [])])}</ul></article>
      </section>
      <footer class="report-audit"><span>Recommendation ID <strong>${item.recommendation_id}</strong></span><span>Snapshot <strong>${item.snapshot_id}</strong></span><span>System <strong>${item.system_version}</strong></span><span>Score model <strong>${item.score_version}</strong></span><span>Review due <strong>${formatSnapshot(item.review_due_at)}</strong></span><span>Adjustment <strong>${item.adjustment_basis}</strong></span><span>Cập nhật <strong>${formatSnapshot(data.snapshot.as_of)}</strong></span></footer>`;
  }

  async function loadRecommendations() {
    if (document.querySelector('[data-verified-recommendations], [data-live-research-radar]')) return;
    const tables = document.querySelectorAll('[data-recommendations]');
    const reports = document.querySelectorAll('[data-stock-report]');
    const performanceTargets = document.querySelectorAll('[data-performance-summary]');
    const performanceMiniTargets = document.querySelectorAll('[data-performance-mini]');
    if (!tables.length && !reports.length && !performanceTargets.length && !performanceMiniTargets.length) return;
    try {
      const [response, tickerAssets] = await Promise.all([
        fetch(siteUrl('public/data/recommendations.json'), { cache: 'no-store' }),
        loadTickerAssets().catch(() => null)
      ]);
      if (!response.ok) throw new Error('Không tải được dữ liệu khuyến nghị');
      const data = await response.json();
      if (publicPayloadBlocked(data)) {
        const master = tickerAssets?.master || {};
        tables.forEach(target => { target.innerHTML = dataReadinessMarkup(master, 'KHUYẾN NGHỊ CÔNG KHAI', true); });
        reports.forEach(target => { target.innerHTML = dataReadinessMarkup(master, 'BÁO CÁO CỔ PHIẾU', true); });
        performanceTargets.forEach(target => { target.innerHTML = dataReadinessMarkup(master, 'HIỆU QUẢ KHUYẾN NGHỊ', true); });
        performanceMiniTargets.forEach(target => { target.innerHTML = dataReadinessMarkup(master, 'HIỆU QUẢ KHUYẾN NGHỊ', true); });
        document.querySelectorAll('[data-recommendation-filter]').forEach(button => { button.closest('.recommendation-filters')?.setAttribute('hidden', ''); });
        if (tables.length) track('recommendation_list_view', { status: 'BLOCKED_DATA_GATE' });
        if (performanceTargets.length || performanceMiniTargets.length) track('performance_view', { status: 'BLOCKED_DATA_GATE' });
        return;
      }
      let activeFilter = 'ALL';
      const redrawTables = () => tables.forEach(target => renderRecommendations(target, data, activeFilter));
      redrawTables();
      document.querySelectorAll('[data-recommendation-filter]').forEach(button => button.addEventListener('click', () => {
        activeFilter = button.dataset.recommendationFilter || 'ALL';
        document.querySelectorAll('[data-recommendation-filter]').forEach(item => item.classList.toggle('is-active', item === button));
        redrawTables();
      }));
      reports.forEach(target => {
        const ticker = String(target.dataset.stockReport || '').toUpperCase();
        const item = data.items.find(record => record.ticker === ticker);
        target.innerHTML = item ? '' : '<div class="empty">Chưa có báo cáo cho mã này.</div>';
        if (item) renderStockReport(target, item, data, tickerAssets?.reportByTicker.get(ticker));
      });
      performanceTargets.forEach(target => renderPerformance(target, data));
      performanceMiniTargets.forEach(target => renderPerformanceMini(target, data));
      if (tables.length) {
        track('recommendation_list_view', { data_status: data.data_status, record_mode: data.items[0]?.record_mode });
        track('recommendation_public_view', { data_status: data.data_status, records: data.items.length });
      }
      if (reports.length) {
        track('stock_report_view', { ticker: reports[0].dataset.stockReport || '', data_status: data.data_status });
        track('sample_premium_report_view', { ticker: reports[0].dataset.stockReport || '', data_status: data.data_status });
      }
      if (performanceTargets.length) {
        track('performance_view', { data_status: data.data_status, total_published: data.performance_summary.total_published });
        track('benchmark_view', { benchmark: 'VNINDEX', data_status: data.data_status });
      }
    } catch (error) {
      [...tables, ...reports, ...performanceTargets, ...performanceMiniTargets].forEach(target => target.innerHTML = `<div class="empty">${error.message}</div>`);
    }
  }

  function normalizeLookupTicker(value) {
    return String(value || '').trim().toUpperCase().replace(/[^A-Z]/g, '').slice(0, 3);
  }

  function isValidStockTicker(value) {
    return /^[A-Z]{3}$/.test(String(value || ''));
  }

  function horizonCards(report) {
    return Object.entries(horizonLabels).map(([horizon, label]) => {
      const view = (report?.horizon_views || []).find(item => item.horizon === horizon);
      return `<article class="lookup-horizon-card">
        <span>${label}</span>
        <strong>${escapeHtml(view?.assessment || 'CHƯA ĐỦ DỮ LIỆU')}</strong>
        <small>${view?.evaluated_at ? formatSnapshot(view.evaluated_at) : 'CHỜ DỮ LIỆU'} · ${escapeHtml(view?.freshness || 'UNKNOWN')}</small>
      </article>`;
    }).join('');
  }

  function quickLookupMarkup(report, security, compact = false) {
    const item = report || {
      ticker: security.ticker,
      company_name: security.company_name,
      sector: security.sector,
      current_price: null,
      rank: null,
      sector_rank: null,
      score: null,
      data_status: 'BLOCKED_DATA_GATE',
      horizon_views: [],
      new_position_state: 'CHƯA ĐỦ DỮ LIỆU',
      holding_state: 'CHƯA ĐỦ DỮ LIỆU'
    };
    const showValues = licensedReportReady(item);
    return `<div class="quick-lookup ${compact ? 'is-compact' : ''}">
      <header><div><span class="panel-label">TRẠNG THÁI · ${escapeHtml(item.data_status)}</span><h2>${escapeHtml(item.ticker)}</h2><p>${escapeHtml(item.company_name)} · ${escapeHtml(item.sector)}</p></div><span class="data-pill">${showValues ? 'DỮ LIỆU ĐÃ KIỂM ĐỊNH' : 'CHỜ DỮ LIỆU ĐƯỢC CẤP QUYỀN'}</span></header>
      <div class="quick-metrics"><div><span>Giá hiện tại</span><strong>${showValues ? formatPrice(item.current_price) : '—'}</strong></div><div><span>Cập nhật</span><strong>${showValues ? formatSnapshot(item.updated_at) : '—'}</strong></div><div><span>Xếp hạng</span><strong>${showValues && item.rank != null ? `#${item.rank}` : '—'}</strong></div><div><span>Hạng ngành</span><strong>${showValues && item.sector_rank != null ? `#${item.sector_rank}` : '—'}</strong></div><div><span>Điểm</span><strong>${showValues && item.score != null ? `${item.score}/100` : '—'}</strong></div></div>
      <div class="lookup-horizon-grid">${horizonCards(item)}</div>
      <div class="position-summary"><div><span>MUA MỚI</span><strong>${escapeHtml(item.new_position_state)}</strong></div><div><span>ĐANG NẮM GIỮ</span><strong>${escapeHtml(item.holding_state)}</strong></div></div>
    </div>`;
  }

  function recommendationHistoryMarkup(ticker, recommendations) {
    const items = recommendations.filter(item => item.ticker === ticker);
    if (!items.length) return '<div class="empty">Chưa có recommendation được công bố cho mã này. Không tạo record để lấp chỗ trống.</div>';
    return `<div class="ticker-history-list">${items.map(item => {
      const performance = performanceValue(item);
      return `<article>
        <div><span>Mã / kỳ hạn</span><strong>${escapeHtml(item.ticker)}</strong><small>${horizonLabels[item.horizon]}</small></div>
        <div><span>Công bố</span><strong>${formatDate(item.publication_date)}</strong></div>
        <div><span>Kích hoạt</span><strong>${item.activation_timestamp ? formatDate(item.activation_timestamp) : 'Chưa kích hoạt'}</strong></div>
        <div><span>Entry</span><strong>${formatPrice(item.performance_entry_price)}</strong></div>
        <div><span>Hiện tại / đóng</span><strong>${formatPrice(performance.group === 'CLOSED' ? item.close_price : item.current_price)}</strong></div>
        <div><span>Kết quả</span><b class="${returnClass(performance.value)}">${performance.label}</b></div>
        <div><span>Review due</span><strong>${formatSnapshot(item.review_due_at)}</strong></div>
        <div><span>Review</span><strong>${escapeHtml(item.review_status || 'PENDING')}</strong><small>${escapeHtml(item.review_decision || 'Chưa có quyết định')}</small></div>
        <div><span>Trạng thái</span><span class="state ${stateClass(item.recommendation_state)}">${stateLabel(item.recommendation_state)}</span></div>
      </article>`;
    }).join('')}</div>`;
  }

  async function loadDynamicStockReport() {
    const target = document.querySelector('[data-dynamic-stock-report]');
    if (!target) return;
    const pathParts = location.pathname.split('/').filter(Boolean);
    const routeTicker = pathParts[pathParts.length - 1] !== 'co-phieu' ? pathParts[pathParts.length - 1] : '';
    const requestedTicker = new URLSearchParams(location.search).get('ticker') || routeTicker;
    const ticker = normalizeLookupTicker(requestedTicker);
    if (!requestedTicker) {
      target.innerHTML = '<div class="empty">Nhập một mã từ trang Kiểm tra cổ phiếu để bắt đầu.</div>';
      return;
    }
    if (!isValidStockTicker(String(requestedTicker).trim().toUpperCase())) {
      target.innerHTML = '<div class="empty">Mã cổ phiếu cần đúng 3 chữ cái.</div>';
      track('ticker_search_invalid', { ticker: String(requestedTicker).slice(0, 12), reason: 'INVALID_FORMAT' });
      return;
    }
    try {
      const assets = await loadTickerAssets();
      rememberTicker(ticker);
      const security = assets.securityByTicker.get(ticker);
      if (!security) {
        document.title = `${ticker} — Trạng thái dữ liệu StockRadar`;
        target.innerHTML = `${tickerAcceptedMarkup(ticker, assets.master)}${dataReadinessMarkup(assets.master, `BÁO CÁO ${ticker}`, true)}<div class="compact-cta"><div><h2>Chưa phát hành kết quả</h2></div><a class="button button-primary" href="kiem-tra-co-phieu/">Tra mã khác</a></div>`;
        track('ticker_search_valid', { ticker, verification_status: 'UNVERIFIED_PUBLIC' });
        return;
      }
      const report = assets.reportByTicker.get(ticker);
      document.title = `${ticker} — StockRadar`;
      if (!licensedReportReady(report)) {
        const lookup = quickLookupMarkup(report, security);
        target.innerHTML = `${lookup}${dataReadinessMarkup(assets.master, `BÁO CÁO ${ticker}`, true)}<div class="compact-cta"><div><h2>Chưa phát hành kết quả</h2></div><a class="button button-primary" href="kiem-tra-co-phieu/">Tra mã khác</a></div>`;
        track('ticker_search_valid', { ticker, data_status: report?.data_status || 'INSUFFICIENT' });
        track('quick_report_view', { ticker, data_status: report?.data_status || 'INSUFFICIENT' });
        return;
      }
      const [recommendationResponse, journalResponse] = await Promise.all([
        fetch(siteUrl('public/data/recommendations.json'), { cache: 'no-store' }),
        fetch(siteUrl('public/data/recommendation-journal.json'), { cache: 'no-store' })
      ]);
      const recommendationPayload = recommendationResponse.ok ? await recommendationResponse.json() : { items: [] };
      const journalPayload = journalResponse.ok ? await journalResponse.json() : { items: [] };
      const recommendations = publicPayloadBlocked(recommendationPayload) ? [] : (recommendationPayload.items || []);
      const journal = publicPayloadBlocked(journalPayload) ? [] : (journalPayload.items || []).filter(item => item.ticker === ticker);
      target.innerHTML = `
        ${quickLookupMarkup(report, security)}
        <section class="position-detail-grid">
          <article><span>MUA MỚI</span><h2>${escapeHtml(report?.new_position_state || 'CHƯA ĐỦ DỮ LIỆU')}</h2><p>${escapeHtml(report?.new_position_note || 'Chưa có dữ liệu để đánh giá điểm mua mới.')}</p></article>
          <article><span>ĐANG NẮM GIỮ</span><h2>${escapeHtml(report?.holding_state || 'CHƯA ĐỦ DỮ LIỆU')}</h2><p>${escapeHtml(report?.holding_note || 'Không suy luận “không mua mới” thành “phải bán”.')}</p></article>
        </section>
        <section class="evidence-grid"><article><span class="panel-label">TẠI SAO?</span><h2>Lý do chính</h2><ul>${(report?.reasons || []).map(item => `<li>${escapeHtml(item)}</li>`).join('') || '<li>Chưa đủ evidence.</li>'}</ul></article><article><span class="panel-label">RỦI RO & ĐIỀU KIỆN ĐỔI</span><h2>Điều cần kiểm tra</h2><ul>${(report?.risks || []).map(item => `<li>${escapeHtml(item)}</li>`).join('') || '<li>Không dùng dữ liệu thiếu cho hành động.</li>'}</ul></article></section>
        <section class="ticker-history"><header><div><span class="panel-label">LỊCH SỬ KHUYẾN NGHỊ CÔNG KHAI</span><h2>Không cherry-pick.</h2></div><a href="hieu-qua/">Xem toàn bộ hiệu quả →</a></header>${recommendationHistoryMarkup(ticker, recommendations)}</section>
        <section class="journal-panel"><header><div><span class="panel-label">NHẬT KÝ BẤT BIẾN</span><h2>${journal.length ? `${journal.length} sự kiện đã ghi` : 'Chưa có sự kiện'}</h2></div></header>${journal.length ? `<ol>${journal.map(item => `<li><time>${formatSnapshot(item.timestamp)}</time><strong>${stateLabel(item.new_state)}</strong><p>${escapeHtml(item.reason)}</p><small>${escapeHtml(item.audit_reference)}</small></li>`).join('')}</ol>` : '<div class="empty">Không có recommendation thì không dựng nhật ký giả.</div>'}</section>
        `;
      track('ticker_search_valid', { ticker, data_status: report?.data_status || 'INSUFFICIENT' });
      track('quick_report_view', { ticker, data_status: report?.data_status || 'INSUFFICIENT' });
      track('four_horizon_view', { ticker });
      track('holding_view', { ticker });
      if (journal.length) track('recommendation_history_view', { ticker, events: journal.length });
    } catch (error) {
      target.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
      track('report_generation_failed', { ticker });
    }
  }

  async function loadTodayChanges() {
    const targets = document.querySelectorAll('[data-today-changes]');
    const riskTargets = document.querySelectorAll('[data-risk-alerts]');
    if (!targets.length && !riskTargets.length) return;
    try {
      const [response, assets] = await Promise.all([
        fetch(siteUrl('public/data/today-changes.json'), { cache: 'no-store' }),
        loadTickerAssets()
      ]);
      if (!response.ok) throw new Error('Không tải được nhật ký thay đổi');
      const data = await response.json();
      if (publicPayloadBlocked(data)) {
        targets.forEach(target => { target.innerHTML = dataReadinessMarkup(assets.master, 'BIẾN ĐỘNG HÔM NAY', true); });
        riskTargets.forEach(target => { target.innerHTML = dataReadinessMarkup(assets.master, 'CẢNH BÁO RỦI RO', true); });
        document.querySelectorAll('[data-today-updated]').forEach(item => { item.textContent = '—'; });
        track('today_changes_view', { status: 'BLOCKED_DATA_GATE', changes: 0 });
        return;
      }
      const markup = items => items.map(item => `<article class="change-card"><time>${formatSnapshot(item.occurred_at)}</time><div><span>${escapeHtml(item.event_type.replaceAll('_', ' '))}</span><h2>${escapeHtml(item.title)}</h2><p>${escapeHtml(item.summary)}</p></div><div class="change-values"><del>${escapeHtml(item.previous_value || '—')}</del><b>→</b><strong>${escapeHtml(item.new_value || '—')}</strong></div></article>`).join('') || '<div class="empty">Không có thay đổi phù hợp.</div>';
      targets.forEach(target => { target.innerHTML = markup(data.items); });
      riskTargets.forEach(target => { target.innerHTML = markup(data.items.filter(item => Number(item.importance || 0) >= 3)); });
      document.querySelectorAll('[data-today-updated]').forEach(item => { item.textContent = formatSnapshot(data.as_of); });
      track('today_changes_view', { data_status: data.data_status, changes: data.items.length });
    } catch (error) {
      [...targets, ...riskTargets].forEach(target => { target.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`; });
    }
  }

  async function loadRecommendationJournal() {
    if (document.querySelector('[data-verified-recommendations], [data-live-research-radar]')) return;
    const target = document.querySelector('[data-recommendation-journal]');
    if (!target) return;
    try {
      const [response, assets] = await Promise.all([
        fetch(siteUrl('public/data/recommendation-journal.json'), { cache: 'no-store' }),
        loadTickerAssets()
      ]);
      const data = await response.json();
      if (publicPayloadBlocked(data)) {
        target.innerHTML = dataReadinessMarkup(assets.master, 'NHẬT KÝ KHUYẾN NGHỊ', true);
        return;
      }
      target.innerHTML = `<ol>${data.items.slice().reverse().map(item => `<li><time>${formatSnapshot(item.timestamp)}</time><div><strong>${escapeHtml(item.ticker)} · ${stateLabel(item.new_state)}</strong><p>${escapeHtml(item.reason)}</p><small>${escapeHtml(item.audit_reference)} · ${escapeHtml(item.system_version)}</small></div></li>`).join('')}</ol>`;
    } catch (_) {
      target.innerHTML = '<div class="empty">Chưa có journal công khai.</div>';
    }
  }

  function wireStockSearch() {
    document.querySelectorAll('[data-stock-search-form]').forEach(form => {
      const result = form.parentElement.querySelector('[data-stock-search-result]');
      const input = form.querySelector('input[name="ticker"]');
      const suggestions = document.createElement('div');
      suggestions.className = 'ticker-suggestions';
      suggestions.setAttribute('role', 'listbox');
      input.after(suggestions);
      let inputStarted = false;

      const submitTicker = async value => {
        const ticker = normalizeLookupTicker(value);
        if (!isValidStockTicker(String(value || '').trim().toUpperCase())) {
          result.className = 'search-result is-unavailable';
          result.innerHTML = '<strong>Mã chưa hợp lệ.</strong><span>Nhập đúng 3 chữ cái.</span>';
          track('ticker_search_invalid', { ticker, reason: 'INVALID_FORMAT' });
          return;
        }
        track('stock_search', { ticker });
        track('ticker_search');
        track('ticker_search_submitted', { ticker });
        rememberTicker(ticker);
        suggestions.innerHTML = '';
        try {
          const assets = await loadTickerAssets();
          const security = assets.securityByTicker.get(ticker);
          if (!security) {
            result.className = 'search-result is-available has-quick-result';
            result.innerHTML = `${tickerAcceptedMarkup(ticker, assets.master, true)}<a class="button button-primary button-small" href="co-phieu/?ticker=${encodeURIComponent(ticker)}">Mở ${escapeHtml(ticker)}</a>`;
            track('ticker_search_valid', { ticker, verification_status: 'UNVERIFIED_PUBLIC' });
            return;
          }
          const report = assets.reportByTicker.get(ticker);
          result.className = 'search-result is-available has-quick-result';
          result.innerHTML = `${quickLookupMarkup(report, security, true)}<a class="button button-primary button-small" href="co-phieu/?ticker=${encodeURIComponent(ticker)}">Mở ${escapeHtml(ticker)}</a>`;
          track('ticker_search_valid', { ticker, data_status: report?.data_status || 'INSUFFICIENT' });
          track('quick_report_view', { ticker, surface: location.pathname });
        } catch (error) {
          result.className = 'search-result is-unavailable';
          result.innerHTML = `<strong>Không tải được lớp tra cứu.</strong><span>${escapeHtml(error.message)}</span>`;
        }
      };

      input.addEventListener('input', async () => {
        if (!inputStarted) { inputStarted = true; track('ticker_input_started'); }
        const query = normalizeLookupTicker(input.value);
        if (!query) { suggestions.innerHTML = ''; return; }
        try {
          const assets = await loadTickerAssets();
          const matches = assets.master.items.filter(item => /^[A-Z]{3}$/.test(item.ticker) && (item.ticker.startsWith(query) || item.company_name.toUpperCase().includes(query))).slice(0, 8);
          suggestions.innerHTML = matches.length
            ? matches.map(item => `<button type="button" role="option" data-ticker-value="${escapeHtml(item.ticker)}"><strong>${escapeHtml(item.ticker)}</strong><span>${escapeHtml(item.company_name)}</span><small>${escapeHtml(item.sector)}</small></button>`).join('')
            : (isValidStockTicker(query) ? `<button type="button" role="option" data-ticker-value="${escapeHtml(query)}"><strong>${escapeHtml(query)}</strong><span>Tra mã này</span><small>CHỜ XÁC MINH</small></button>` : '');
        } catch (_) { suggestions.innerHTML = ''; }
      });
      suggestions.addEventListener('click', event => {
        const option = event.target.closest('[data-ticker-value]');
        if (!option) return;
        input.value = option.dataset.tickerValue;
        suggestions.innerHTML = '';
        track('ticker_autocomplete_selected', { ticker: input.value });
        submitTicker(input.value);
      });
      form.addEventListener('submit', event => { event.preventDefault(); submitTicker(input.value); });
      const preset = new URLSearchParams(location.search).get('ticker');
      if (preset) { input.value = preset; submitTicker(preset); }
    });
  }

  async function loadRadar() {
    if (document.querySelector('[data-live-research-radar]')) return;
    const hasRankedSurface = Boolean(document.querySelector('[data-radar-list], [data-radar-table]'));
    const targets = document.querySelectorAll('[data-radar-list], [data-radar-table], [data-market], [data-coverage], [data-snapshot], [data-grade], [data-status]');
    if (!targets.length) return;
    try {
      const [response, assets] = await Promise.all([
        fetch(siteUrl('public/data/radar.json'), { cache: 'no-store' }),
        loadTickerAssets()
      ]);
      if (!response.ok) throw new Error('Không tải được dữ liệu Radar');
      const data = await response.json();
      if (!publicMarketDataReady(data)) {
        const reference = internalReference(assets.master);
        document.querySelectorAll('[data-radar-list], [data-radar-table]').forEach(el => {
          el.classList.remove('loading');
          el.innerHTML = dataReadinessMarkup(assets.master, 'RADAR TOÀN HOSE', true);
        });
        document.querySelectorAll('[data-radar-filter]').forEach(button => {
          button.disabled = true;
          button.setAttribute('aria-disabled', 'true');
        });
        document.querySelectorAll('[data-market]').forEach(el => { el.textContent = 'CHỜ DỮ LIỆU'; });
        document.querySelectorAll('[data-coverage]').forEach(el => { el.textContent = reference.coverage_pct == null ? '—' : `${reference.coverage_pct}%`; });
        document.querySelectorAll('[data-snapshot]').forEach(el => { el.textContent = formatSnapshot(reference.as_of); });
        document.querySelectorAll('[data-grade]').forEach(el => { el.textContent = 'INTERNAL REFERENCE'; });
        document.querySelectorAll('[data-status]').forEach(el => { el.textContent = 'DATA GATE'; });
        if (hasRankedSurface) track('radar_view', { status: 'BLOCKED_DATA_GATE' });
        return;
      }
      document.querySelectorAll('[data-radar-list]').forEach(el => renderMiniRadar(el, data));
      let activeFilter = 'ALL';
      const redrawTables = () => document.querySelectorAll('[data-radar-table]').forEach(el => renderRadarTable(el, data, activeFilter));
      redrawTables();
      document.querySelectorAll('[data-radar-filter]').forEach(button => button.addEventListener('click', () => {
        activeFilter = button.dataset.radarFilter || 'ALL';
        document.querySelectorAll('[data-radar-filter]').forEach(item => item.classList.toggle('is-active', item === button));
        redrawTables();
      }));
      document.querySelectorAll('[data-market]').forEach(el => el.textContent = marketLabel(data.market_regime));
      document.querySelectorAll('[data-coverage]').forEach(el => el.textContent = `${data.snapshot.universe_coverage_pct}%`);
      document.querySelectorAll('[data-snapshot]').forEach(el => el.textContent = formatSnapshot(data.snapshot.as_of));
      document.querySelectorAll('[data-grade]').forEach(el => el.textContent = data.snapshot.data_grade);
      document.querySelectorAll('[data-status]').forEach(el => el.textContent = statusLabel(data.status));
      if (hasRankedSurface) {
        track('radar_view', { status: data.status, data_status: data.data_status });
        track('top_view', { status: data.status, data_status: data.data_status });
      }
    } catch (error) {
      targets.forEach(el => el.innerHTML = `<div class="empty">${error.message}</div>`);
    }
  }

  async function loadTrackRecord() {
    const target = document.querySelector('[data-track-record]');
    if (!target) return;
    try {
      const [response, assets] = await Promise.all([
        fetch(siteUrl('public/data/track-record.json'), { cache: 'no-store' }),
        loadTickerAssets()
      ]);
      const data = await response.json();
      if (publicPayloadBlocked(data)) {
        target.innerHTML = dataReadinessMarkup(assets.master, 'LỊCH SỬ CÔNG KHAI', true);
        track('track_record_view', { status: 'BLOCKED_DATA_GATE' });
        return;
      }
      target.innerHTML = `
        <div class="table-row history-row table-head"><span>Hạng</span><span>Mã</span><span>Điểm</span><span>Trạng thái</span><span>Snapshot</span></div>
        ${data.rows.map(row => `
          <div class="table-row history-row">
            <strong class="rank">#${row.rank}</strong>
            <div><div class="table-ticker">${row.ticker}</div><div class="setup">${statusLabel(row.release_status)}</div></div>
            <strong class="score">${row.score}</strong>
            <span><span class="state ${stateClass(row.state)}">${stateLabel(row.state)}</span></span>
            <span class="change">${new Date(row.as_of).toLocaleDateString('vi-VN')}</span>
          </div>`).join('')}`;
      track('track_record_view', { data_status: data.data_status });
    } catch (_) {
      target.innerHTML = '<div class="empty">Chưa có track record công khai.</div>';
    }
  }

  function wireForms() {
    document.querySelectorAll('[data-signup-form]').forEach(form => {
      const params = new URLSearchParams(location.search);
      const requestedTicker = normalizeLookupTicker(params.get('ticker'));
      if (requestedTicker && form.elements.watch_tickers) form.elements.watch_tickers.value = requestedTicker;
      if (params.get('tier') === 'trial' && form.elements.requested_tier) form.elements.requested_tier.value = 'TRIAL';
      form.querySelectorAll('input[name="preferred_sectors"]').forEach(input => input.addEventListener('change', () => {
        const checked = form.querySelectorAll('input[name="preferred_sectors"]:checked');
        if (checked.length > 3) {
          input.checked = false;
          const message = form.querySelector('[data-form-message]');
          message.className = 'form-message error';
          message.textContent = 'Onboarding chỉ cho phép chọn tối đa 3 ngành.';
        }
      }));
      let started = false;
      form.addEventListener('input', () => {
        if (!started) { started = true; track('signup_started'); track('signup_start'); }
      }, { once: true });
      form.addEventListener('submit', async event => {
        event.preventDefault();
        const message = form.querySelector('[data-form-message]');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        data.preferred_horizons = formData.getAll('preferred_horizons');
        data.preferred_sectors = formData.getAll('preferred_sectors');
        data.watch_tickers = String(formData.get('watch_tickers') || '').split(',').map(item => normalizeLookupTicker(item)).filter(Boolean).slice(0, 3);
        data.consent = form.querySelector('[name="consent"]')?.checked || false;
        data.alert_opt_in = form.querySelector('[name="alert_opt_in"]')?.checked || false;
        data.product_email_consent = form.querySelector('[name="product_email_consent"]')?.checked || false;
        if (data.requested_tier === 'FREE') data.product_email_consent = false;
        data.utm = getUtm();
        data.preferred_horizons.forEach(horizon => track('onboarding_horizon_selected', { horizon }));
        data.preferred_sectors.forEach(sector => track('onboarding_sector_selected', { sector }));
        data.watch_tickers.forEach(ticker => track('onboarding_ticker_added', { ticker }));
        message.className = 'form-message';
        const endpoint = apiUrl('api/signup');
        if (!endpoint) {
          message.className = 'form-message error';
          message.textContent = 'Biểu mẫu đang chờ kết nối backend bảo mật. Website chưa nhận hoặc lưu thông tin đăng ký.';
          return;
        }
        message.textContent = 'Đang ghi nhận…';
        try {
          const response = await fetch(endpoint, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data)
          });
          const result = await response.json();
          if (!response.ok) throw new Error(result.error || 'Không thể ghi nhận đăng ký');
          message.className = 'form-message success';
          message.textContent = 'Đã ghi nhận. Khi có bản thử nghiệm phù hợp, StockRadar sẽ liên hệ theo thông tin bạn đã chọn.';
          track('signup_completed', { proposition: data.proposition });
          track('signup_complete', { proposition: data.proposition });
          if (data.alert_opt_in) track('alert_opt_in', { proposition: data.proposition });
          form.reset();
        } catch (error) {
          message.className = 'form-message error';
          message.textContent = `${error.message}. Bản tĩnh cần backend được triển khai để nhận đăng ký.`;
        }
      });
    });
  }

  function wireNavigation() {
    const toggle = document.querySelector('[data-nav-toggle]');
    const menu = document.querySelector('[data-nav-menu]');
    if (!toggle || !menu) return;

    const close = () => {
      menu.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
    };
    toggle.addEventListener('click', () => {
      const opening = !menu.classList.contains('is-open');
      menu.classList.toggle('is-open', opening);
      toggle.setAttribute('aria-expanded', String(opening));
    });
    menu.addEventListener('click', event => {
      if (event.target.closest('a')) close();
    });
    document.addEventListener('click', event => {
      if (!menu.contains(event.target) && !toggle.contains(event.target)) close();
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') {
        close();
        toggle.focus();
      }
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    getUtm(); retentionEvents();
    track('landing_view');
    mountPortalShell();
    wireNavigation();
    if (/(^|\/)pro\/?$/.test(location.pathname)) { track('pro_page_view'); track('pro_view'); }
    if (/(^|\/)nganh\/?$/.test(location.pathname)) track('sector_view');
    if (document.body.dataset.pageKind === 'email') track('email_view');
    document.querySelectorAll('.horizon-tab').forEach(el => el.addEventListener('click', () => track('horizon_change', { label: el.textContent.trim() })));
    document.querySelectorAll('[data-track-event]').forEach(el => el.addEventListener('click', () => track(el.dataset.trackEvent, { target: el.getAttribute('href') || '' })));
    renderRecentTickers(); loadDataReadiness(); loadRadar(); loadTrackRecord(); loadRecommendations(); loadDynamicStockReport();
    loadTodayChanges(); loadRecommendationJournal(); wireStockSearch(); wireForms();
  });
})();
