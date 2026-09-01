(() => {
  const apiMode = document.documentElement.dataset.apiMode || 'auto';
  const allowedEvents = new Set([
    'ad_click', 'landing_view', 'radar_view', 'top5_expand', 'track_record_view',
    'signup_started', 'signup_completed', 'alert_opt_in', 'pro_page_view',
    'trial_started', 'subscription_started', 'return_d1', 'return_d7',
    'knowledge_view', 'method_view', 'horizon_select', 'stock_search',
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
    if (value === 'SHORTLIST_FROM_AVAILABLE_DATA') return 'DANH SÁCH MINH HỌA';
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

  function pricePosition(item) {
    if (item.current_price == null) return 'Chưa có quan sát giá mới.';
    if (item.current_price < item.recommended_buy_low) return 'Giá hiện dưới vùng mua đã công bố; chưa tự động kích hoạt.';
    if (item.current_price > item.recommended_buy_high) return 'Giá hiện trên vùng mua đã công bố; không suy diễn thành điểm mua mới.';
    return 'Giá hiện nằm trong vùng mua đã công bố; activation vẫn căn cứ lần chạm đầu tiên sau công bố.';
  }

  function priceRange(low, high) {
    if (low == null || high == null) return '—';
    return `${formatPrice(low)}–${formatPrice(high)}`;
  }

  function mountPortalShell() {
    const header = document.querySelector('.site-header');
    if (!header || document.querySelector('.portal-utility')) return;

    const menu = header.querySelector('[data-nav-menu]');
    if (menu) {
      const route = location.pathname.replace(/\/+$/, '');
      const items = [
        ['radar5/', 'Radar', '/radar5'],
        ['kiem-tra-co-phieu/', 'Tra mã', '/kiem-tra-co-phieu'],
        ['khuyen-nghi/', 'Khuyến nghị', '/khuyen-nghi'],
        ['thay-doi-hom-nay/', 'Biến động', '/thay-doi-hom-nay'],
        ['hieu-qua/', 'Hiệu quả', '/hieu-qua'],
        ['theo-doi/', 'Theo dõi', '/theo-doi'],
        ['tai-khoan/', 'Tài khoản', '/tai-khoan'],
      ];
      menu.innerHTML = items.map(([href, label, match]) => {
        const isCurrent = route.endsWith(match)
          || route.includes(`${match}/`)
          || (match === '/kiem-tra-co-phieu' && (route.includes('/co-phieu/') || route.includes('/phan-tich')));
        return `<a href="${href}"${isCurrent ? ' aria-current="page"' : ''}>${label}</a>`;
      }).join('') + '<a class="button button-primary button-small" href="pro/">Nâng cấp</a>';
    }

    const utility = document.createElement('div');
    utility.className = 'portal-utility';
    utility.innerHTML = `<div class="container portal-utility-inner"><span><strong>STOCKRADAR.VN</strong><i></i>Radar cổ phiếu Việt Nam</span><span class="portal-utility-note">HOSE · Ngắn hạn · Trung hạn · Dài hạn · Tích sản</span></div>`;

    const tape = document.createElement('section');
    tape.className = 'market-tape';
    tape.setAttribute('aria-label', 'Trạng thái dữ liệu StockRadar');
    tape.innerHTML = `<div class="container market-tape-inner" aria-live="polite"><div class="tape-heading"><span class="live-dot" aria-hidden="true"></span><span>THỊ TRƯỜNG</span></div><div class="tape-item"><strong data-market>—</strong></div><div class="tape-item tape-snapshot"><span>Cập nhật</span><strong data-snapshot>—</strong></div><div class="tape-disclaimer">Dữ liệu minh họa</div></div>`;

    const subnav = document.createElement('nav');
    subnav.className = 'product-subnav';
    subnav.setAttribute('aria-label', 'Điều hướng phân tích');
    subnav.innerHTML = `<div class="container product-subnav-inner"><a href="radar5/">Ngắn hạn</a><a href="kiem-tra-co-phieu/">Trung hạn</a><a href="kiem-tra-co-phieu/">Dài hạn</a><a href="kiem-tra-co-phieu/">Tích sản</a><a href="nganh/">Theo ngành</a><a href="track-record/">Lịch sử</a><a href="pro/">Gói dịch vụ</a></div>`;

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

  function renderRadarTable(target, data) {
    if (!target) return;
    target.innerHTML = `
      <div class="table-row table-head"><span>Hạng</span><span>Mã / thiết lập</span><span>Điểm</span><span>Trạng thái</span><span>Giá demo</span><span>Cách pivot</span><span>Thay đổi</span></div>
      ${data.items.map(item => `
        <article class="table-row" data-ticker="${item.ticker}">
          <strong class="rank">#${item.rank}</strong>
          <div><a class="table-ticker ticker-link" href="phan-tich/?ticker=${encodeURIComponent(item.ticker)}">${item.ticker}</a><div class="setup">${item.setup} · ${item.reason}</div></div>
          <strong class="score">${item.score}</strong>
          <span><span class="state ${stateClass(item.state)}">${stateLabel(item.state)}</span></span>
          <span class="demo-price">${Number(item.current_price).toLocaleString('vi-VN')}</span>
          <span class="pivot-distance">${Number(item.distance_to_pivot_pct).toLocaleString('vi-VN')}%</span>
          <span class="change ${item.state_change === 'UNCHANGED' ? 'unchanged' : ''}">${item.state_change === 'UNCHANGED' ? stateLabel(item.state_change) : item.state_change.split('→').map(stateLabel).join(' → ')}</span>
        </article>`).join('')}`;
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
    const activated = data.items.filter(item => lifecycleGroup(item) !== 'UNACTIVATED');
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
      <section class="performance-summary-grid" aria-label="Tóm tắt hiệu quả mô phỏng">
        <article><span>Tổng công bố</span><strong>${summary.total_published}</strong><small>SHADOW records</small></article>
        <article><span>Chưa kích hoạt</span><strong>${summary.unactivated}</strong><small>Không tính lãi/lỗ</small></article>
        <article><span>Đang mở</span><strong>${summary.open}</strong><small>Mark-to-market</small></article>
        <article><span>Đã đóng</span><strong>${summary.closed}</strong><small>Kết quả đã khóa</small></article>
        <article><span>Tỷ lệ thắng</span><strong>${formatPercent(summary.win_rate_pct, false)}</strong><small>Chỉ record đã đóng</small></article>
        <article><span>Lợi nhuận đóng TB</span><strong class="${returnClass(summary.average_closed_return_pct)}">${formatPercent(summary.average_closed_return_pct)}</strong><small>Không phải track record thật</small></article>
      </section>
      <section class="performance-method-note"><div><span class="panel-label">PHƯƠNG PHÁP CỐ ĐỊNH</span><h2>Công bố → chạm vùng mua → kích hoạt → đóng</h2><p>Giá entry là giao dịch hợp lệ đầu tiên sau công bố chạm vùng mua. ${activated.length} record đã kích hoạt; record chưa kích hoạt không có P/L và không đi vào mẫu tính tỷ lệ thắng.</p></div><span class="data-pill">${data.record_mode || data.items[0]?.record_mode || 'SHADOW'} · ${data.recommendation_mode}</span></section>
      <section class="performance-breakdown"><header><div><span class="panel-label">THEO CHÂN TRỜI</span><h2>Mỗi mục tiêu là một mẫu riêng</h2></div></header>${horizons}</section>
      <section class="performance-table"><div class="performance-row performance-head"><span>Mã</span><span>Công bố</span><span>Kích hoạt</span><span>Entry</span><span>Hiện tại / đóng</span><span>Lãi / lỗ</span><span>Benchmark</span><span>Vượt chuẩn</span><span>Trạng thái</span></div>${rows}</section>
      <p class="performance-footnote">Dữ liệu MOCK/SHADOW chỉ kiểm thử phương pháp. Corporate action được xử lý theo adjustment basis; record đã đóng dùng giá đóng đã khóa và không đổi theo giá hiện tại về sau.</p>`;
  }

  function renderPerformanceMini(target, data) {
    const summary = data.performance_summary;
    target.innerHTML = `
      <div class="home-proof-stats"><div><span>Công bố</span><strong>${summary.total_published}</strong></div><div><span>Chưa kích hoạt</span><strong>${summary.unactivated}</strong></div><div><span>Đã đóng</span><strong>${summary.closed}</strong></div><div><span>Tỷ lệ thắng*</span><strong>${formatPercent(summary.win_rate_pct, false)}</strong></div></div>
      <div class="home-proof-list">${data.items.slice(0, 3).map(item => {
        const performance = performanceValue(item);
        return `<a href="co-phieu/?ticker=${encodeURIComponent(item.ticker)}"><span><strong>${item.ticker}</strong><small>${horizonLabels[item.horizon]}</small></span><span class="state ${stateClass(item.recommendation_state)}">${stateLabel(item.recommendation_state)}</span><b class="${returnClass(performance.value)}">${performance.label}</b></a>`;
      }).join('')}</div>
      <small class="home-proof-note">* Chỉ tính record đã đóng; loại record chưa kích hoạt. Toàn bộ là MOCK/SHADOW.</small>`;
  }

  function renderStockReport(target, item, data, stockReport = null) {
    const views = new Map((stockReport?.horizon_views || []).map(view => [view.horizon, view]));
    const horizonTabs = Object.entries(horizonLabels).map(([value, label]) => {
      const view = views.get(value);
      return `
      <div class="report-horizon ${value === item.horizon ? 'is-active' : ''}">
        <strong>${label}</strong><span>${escapeHtml(view?.assessment || (value === item.horizon ? 'Record demo hiện tại' : 'Chưa đủ dữ liệu'))}</span>
        <small>${view?.evaluated_at ? formatSnapshot(view.evaluated_at) : 'Chưa đánh giá'}</small>
      </div>`;
    }).join('');
    const list = values => (values || []).map(value => `<li>${value}</li>`).join('');
    const performance = performanceValue(item);
    const activationText = item.activation_timestamp
      ? `Đã kích hoạt lúc ${formatSnapshot(item.activation_timestamp)} tại ${formatPrice(item.performance_entry_price)}.`
      : 'Chưa có giao dịch hợp lệ sau công bố đi vào vùng mua; chưa phát sinh P/L.';
    const resultText = performance.group === 'CLOSED'
      ? `Đã đóng tại ${formatPrice(item.close_price)} ngày ${formatSnapshot(item.close_timestamp)}; kết quả ${formatPercent(item.final_return_pct)} đã được khóa.`
      : performance.group === 'OPEN'
        ? `Đang mở với P/L ${formatPercent(item.current_return_pct)} từ entry hiệu quả.`
        : 'Chưa kích hoạt nên không hiển thị lãi/lỗ.';
    target.innerHTML = `
      <section class="report-overview">
        <div class="report-title"><div><span class="panel-label">BÁO CÁO CỔ PHIẾU · MÔ PHỎNG</span><h1>${item.ticker}</h1><p>${item.company_name} · ${item.sector}</p></div><span class="state ${stateClass(item.recommendation_state)}">${stateLabel(item.recommendation_state)}</span></div>
        <div class="report-metrics">
          <div><span>Giá hiện tại demo</span><strong>${formatPrice(item.current_price)}</strong></div>
          <div><span>Điểm nghiên cứu</span><strong>${formatPrice(item.stock_score)}<small>/100 · không phải xác suất</small></strong></div>
          <div><span>Xếp hạng mục tiêu</span><strong>#${item.rank}</strong></div>
          <div><span>Trạng thái thị trường</span><strong>${marketLabel(item.market_regime)}</strong></div>
          <div><span>P/L theo record</span><strong class="${returnClass(performance.value)}">${performance.label}</strong></div>
          <div><span>Cấp / chế độ</span><strong>${item.data_grade} · ${item.record_mode}</strong></div>
        </div>
      </section>
      <div class="report-horizons">${horizonTabs}</div>
      <section class="recommendation-plan">
        <header><div><span class="panel-label">KẾ HOẠCH CÓ ĐIỀU KIỆN</span><h2>${horizonLabels[item.horizon]}</h2></div><span class="data-pill">RESEARCH_ONLY · MOCK</span></header>
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
      <section class="report-answers" aria-label="Các câu hỏi kiểm chứng của báo cáo StockRadar">
        <article><span>01 · ĐÁNH GIÁ</span><h2>Đánh giá hiện tại?</h2><p>${stateLabel(item.recommendation_state)}. ${resultText}</p></article>
        <article><span>02 · MUA MỚI</span><h2>Nếu chưa có cổ phiếu?</h2><p><strong>${escapeHtml(item.new_position_state)}</strong>. ${escapeHtml(item.new_position_note)}</p></article>
        <article><span>03 · ĐANG NẮM GIỮ</span><h2>Nếu đang sở hữu?</h2><p><strong>${escapeHtml(item.holding_state)}</strong>. ${escapeHtml(item.holding_note)}</p></article>
        <article><span>04 · XẾP HẠNG</span><h2>Đứng ở đâu trong mục tiêu?</h2><p>Hạng #${item.rank} của mô hình ${horizonLabels[item.horizon]}, điểm ${formatPrice(item.stock_score)}/100 với độ phủ ${formatPrice(item.score_coverage_pct)}%.</p></article>
        <article><span>05 · VỊ TRÍ GIÁ</span><h2>Giá đang ở đâu?</h2><p>${pricePosition(item)}</p></article>
        <article><span>06 · HÀNH ĐỘNG</span><h2>Vùng mua và entry?</h2><p>Vùng ${priceRange(item.recommended_buy_low, item.recommended_buy_high)}. ${activationText}</p></article>
        <article><span>07 · MỤC TIÊU</span><h2>Mốc nào cần theo dõi?</h2><p>Mục tiêu ${formatPrice(item.target_price)}; ${item.stop_loss == null ? 'điểm vô hiệu theo thay đổi luận điểm.' : `mức quản trị ${formatPrice(item.stop_loss)}.`}</p></article>
        <article><span>08 · LUẬN ĐIỂM</span><h2>Vì sao được chọn?</h2><ul>${list(item.thesis)}</ul></article>
        <article class="is-risk"><span>09 · RỦI RO</span><h2>Rủi ro chính là gì?</h2><ul>${list(item.risks)}</ul></article>
        <article class="is-change"><span>10 · VÔ HIỆU</span><h2>Điều gì làm nhận định đổi?</h2><ul>${list(item.invalidation_conditions)}</ul></article>
        <article><span>11 · LỊCH SỬ</span><h2>Record trước được lưu thế nào?</h2><p>${resultText} VN-Index ${formatPercent(item.benchmark_return_pct)}; vượt chuẩn ${formatPercent(item.excess_return_pct)}.</p><a class="text-link" href="khuyen-nghi/#nhat-ky">Mở nhật ký bất biến →</a></article>
      </section>
      <footer class="report-audit"><span>Recommendation ID <strong>${item.recommendation_id}</strong></span><span>Snapshot <strong>${item.snapshot_id}</strong></span><span>System <strong>${item.system_version}</strong></span><span>Score model <strong>${item.score_version}</strong></span><span>Review due <strong>${formatSnapshot(item.review_due_at)}</strong></span><span>Adjustment <strong>${item.adjustment_basis}</strong></span><span>Cập nhật <strong>${formatSnapshot(data.snapshot.as_of)}</strong></span></footer>`;
  }

  async function loadRecommendations() {
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
        target.innerHTML = item ? '' : '<div class="empty">Chưa có báo cáo mô phỏng cho mã này.</div>';
        if (item) renderStockReport(target, item, data, tickerAssets?.reportByTicker.get(ticker));
      });
      performanceTargets.forEach(target => renderPerformance(target, data));
      performanceMiniTargets.forEach(target => renderPerformanceMini(target, data));
      if (tables.length) {
        track('recommendation_list_view', { is_mock: data.is_mock, record_mode: data.items[0]?.record_mode });
        track('recommendation_public_view', { is_mock: data.is_mock, records: data.items.length });
      }
      if (reports.length) {
        track('stock_report_view', { ticker: reports[0].dataset.stockReport || '', is_mock: data.is_mock });
        track('sample_premium_report_view', { ticker: reports[0].dataset.stockReport || '', is_mock: data.is_mock });
      }
      if (performanceTargets.length) {
        track('performance_view', { is_mock: data.is_mock, total_published: data.performance_summary.total_published });
        track('benchmark_view', { benchmark: 'VNINDEX', is_mock: data.is_mock });
      }
    } catch (error) {
      [...tables, ...reports, ...performanceTargets, ...performanceMiniTargets].forEach(target => target.innerHTML = `<div class="empty">${error.message}</div>`);
    }
  }

  function normalizeLookupTicker(value) {
    return String(value || '').trim().toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 12);
  }

  function horizonCards(report) {
    return Object.entries(horizonLabels).map(([horizon, label]) => {
      const view = (report?.horizon_views || []).find(item => item.horizon === horizon);
      return `<article class="lookup-horizon-card">
        <span>${label}</span>
        <strong>${escapeHtml(view?.assessment || 'CHƯA ĐỦ DỮ LIỆU')}</strong>
        <p>${escapeHtml(view?.summary || 'Không bịa kết luận khi chưa đủ bằng chứng.')}</p>
        <small>${view?.evaluated_at ? `Đánh giá: ${formatSnapshot(view.evaluated_at)}` : 'Chưa có lần đánh giá đạt chuẩn'} · ${escapeHtml(view?.freshness || 'UNKNOWN')}</small>
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
      data_status: 'INSUFFICIENT',
      horizon_views: [],
      new_position_state: 'CHƯA ĐỦ DỮ LIỆU',
      holding_state: 'CHƯA ĐỦ DỮ LIỆU'
    };
    return `<div class="quick-lookup ${compact ? 'is-compact' : ''}">
      <header><div><span class="panel-label">ĐÁNH GIÁ NHANH · ${escapeHtml(item.data_status)}</span><h2>${escapeHtml(item.ticker)}</h2><p>${escapeHtml(item.company_name)} · ${escapeHtml(item.sector)}</p></div><span class="data-pill">${item.current_price == null ? 'CHƯA CÓ GIÁ ĐƯỢC CẤP QUYỀN' : `MOCK ${formatPrice(item.current_price)}`}</span></header>
      <div class="quick-metrics"><div><span>Giá hiện tại</span><strong>${formatPrice(item.current_price)}</strong></div><div><span>Cập nhật</span><strong>${formatSnapshot(item.updated_at)}</strong></div><div><span>Xếp hạng</span><strong>${item.rank == null ? '—' : `#${item.rank}`}</strong></div><div><span>Hạng ngành</span><strong>${item.sector_rank == null ? '—' : `#${item.sector_rank}`}</strong></div><div><span>Điểm</span><strong>${item.score == null ? '—' : `${item.score}/100`}</strong></div></div>
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
    const ticker = normalizeLookupTicker(new URLSearchParams(location.search).get('ticker') || routeTicker);
    if (!ticker) {
      target.innerHTML = '<div class="empty">Nhập một mã từ trang Kiểm tra cổ phiếu để bắt đầu.</div>';
      return;
    }
    try {
      const [assets, recommendationResponse, journalResponse] = await Promise.all([
        loadTickerAssets(),
        fetch(siteUrl('public/data/recommendations.json'), { cache: 'no-store' }),
        fetch(siteUrl('public/data/recommendation-journal.json'), { cache: 'no-store' })
      ]);
      const security = assets.securityByTicker.get(ticker);
      if (!security) {
        const boundary = assets.master.full_universe
          ? 'Mã này hiện không thuộc phạm vi cổ phiếu HOSE mà StockRadar hỗ trợ.'
          : 'Fixture công khai chưa phải security master HOSE đầy đủ, nên StockRadar chưa thể xác minh mã này trên bản tĩnh.';
        target.innerHTML = `<div class="blocked-banner"><div><strong>KHÔNG TẠO BÁO CÁO</strong>${escapeHtml(boundary)}</div><span>DATA GATE</span></div><div class="compact-cta"><div><h2>Tra mã khác</h2><p>Không tự chuyển sang HNX/UPCOM và không bịa dữ liệu.</p></div><a class="button button-primary" href="kiem-tra-co-phieu/">Mở tra cứu</a></div>`;
        track('ticker_search_invalid', { ticker, full_universe: assets.master.full_universe });
        return;
      }
      const report = assets.reportByTicker.get(ticker);
      const recommendations = recommendationResponse.ok ? (await recommendationResponse.json()).items : [];
      const journalPayload = journalResponse.ok ? await journalResponse.json() : { items: [] };
      const journal = journalPayload.items.filter(item => item.ticker === ticker);
      document.title = `${ticker} — Bốn góc nhìn StockRadar`;
      target.innerHTML = `
        ${quickLookupMarkup(report, security)}
        <section class="position-detail-grid">
          <article><span>MUA MỚI</span><h2>${escapeHtml(report?.new_position_state || 'CHƯA ĐỦ DỮ LIỆU')}</h2><p>${escapeHtml(report?.new_position_note || 'Chưa có dữ liệu để đánh giá điểm mua mới.')}</p></article>
          <article><span>ĐANG NẮM GIỮ</span><h2>${escapeHtml(report?.holding_state || 'CHƯA ĐỦ DỮ LIỆU')}</h2><p>${escapeHtml(report?.holding_note || 'Không suy luận “không mua mới” thành “phải bán”.')}</p></article>
        </section>
        <section class="evidence-grid"><article><span class="panel-label">TẠI SAO?</span><h2>Lý do chính</h2><ul>${(report?.reasons || []).map(item => `<li>${escapeHtml(item)}</li>`).join('') || '<li>Chưa đủ evidence.</li>'}</ul></article><article><span class="panel-label">RỦI RO & ĐIỀU KIỆN ĐỔI</span><h2>Điều cần kiểm tra</h2><ul>${(report?.risks || []).map(item => `<li>${escapeHtml(item)}</li>`).join('') || '<li>Không dùng dữ liệu thiếu cho hành động.</li>'}</ul></article></section>
        <section class="ticker-history"><header><div><span class="panel-label">LỊCH SỬ KHUYẾN NGHỊ CÔNG KHAI</span><h2>Không cherry-pick.</h2></div><a href="hieu-qua/">Xem toàn bộ hiệu quả →</a></header>${recommendationHistoryMarkup(ticker, recommendations)}</section>
        <section class="journal-panel"><header><div><span class="panel-label">NHẬT KÝ BẤT BIẾN</span><h2>${journal.length ? `${journal.length} sự kiện đã ghi` : 'Chưa có sự kiện'}</h2></div></header>${journal.length ? `<ol>${journal.map(item => `<li><time>${formatSnapshot(item.timestamp)}</time><strong>${stateLabel(item.new_state)}</strong><p>${escapeHtml(item.reason)}</p><small>${escapeHtml(item.audit_reference)}</small></li>`).join('')}</ol>` : '<div class="empty">Không có recommendation thì không dựng nhật ký giả.</div>'}</section>
        <section class="ticker-trial-cta"><div><span class="panel-label">THEO DÕI THEO MÃ</span><h2>Theo dõi ${escapeHtml(ticker)} miễn phí 7 ngày</h2><p>Trial chỉ nhận email sau khi xác minh và đồng ý; Free không nhận email nội dung hằng ngày.</p></div><a class="button button-primary" data-track-event="ticker_trial_cta_clicked" href="signup/?tier=trial&ticker=${encodeURIComponent(ticker)}">Bắt đầu dùng thử</a></section>`;
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
    const target = document.querySelector('[data-today-changes]');
    if (!target) return;
    try {
      const response = await fetch(siteUrl('public/data/today-changes.json'), { cache: 'no-store' });
      if (!response.ok) throw new Error('Không tải được nhật ký thay đổi');
      const data = await response.json();
      target.innerHTML = data.items.map(item => `<article class="change-card"><time>${formatSnapshot(item.occurred_at)}</time><div><span>${escapeHtml(item.event_type.replaceAll('_', ' '))}</span><h2>${escapeHtml(item.title)}</h2><p>${escapeHtml(item.summary)}</p></div><div class="change-values"><del>${escapeHtml(item.previous_value || '—')}</del><b>→</b><strong>${escapeHtml(item.new_value || '—')}</strong></div></article>`).join('') || '<div class="empty">Hôm nay chưa có thay đổi đủ ý nghĩa để hiển thị.</div>';
      document.querySelectorAll('[data-today-updated]').forEach(item => { item.textContent = formatSnapshot(data.as_of); });
      track('today_changes_view', { is_mock: data.is_mock, changes: data.items.length });
    } catch (error) {
      target.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
    }
  }

  async function loadRecommendationJournal() {
    const target = document.querySelector('[data-recommendation-journal]');
    if (!target) return;
    try {
      const response = await fetch(siteUrl('public/data/recommendation-journal.json'), { cache: 'no-store' });
      const data = await response.json();
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
        if (!ticker) return;
        track('stock_search', { ticker });
        track('ticker_search');
        track('ticker_search_submitted', { ticker });
        suggestions.innerHTML = '';
        try {
          const assets = await loadTickerAssets();
          const security = assets.securityByTicker.get(ticker);
          if (!security) {
            result.className = 'search-result is-unavailable';
            const message = assets.master.full_universe
              ? 'Mã này hiện không thuộc phạm vi cổ phiếu HOSE mà StockRadar hỗ trợ.'
              : 'Bản tĩnh đang dùng fixture lookup, chưa phải security master HOSE đầy đủ. Không thể xác minh mã này và không tạo dữ liệu giả.';
            result.innerHTML = `<strong>${escapeHtml(ticker)}: chưa thể xác minh.</strong><span>${escapeHtml(message)}</span><a href="kiem-tra-co-phieu/">Xem phạm vi dữ liệu →</a>`;
            track('ticker_search_invalid', { ticker, full_universe: assets.master.full_universe });
            return;
          }
          const report = assets.reportByTicker.get(ticker);
          result.className = 'search-result is-available has-quick-result';
          result.innerHTML = `${quickLookupMarkup(report, security, true)}<a class="button button-primary button-small" href="co-phieu/?ticker=${encodeURIComponent(ticker)}">Xem báo cáo ${escapeHtml(ticker)}</a>`;
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
          const matches = assets.master.items.filter(item => item.ticker.startsWith(query) || item.company_name.toUpperCase().includes(query)).slice(0, 8);
          suggestions.innerHTML = matches.map(item => `<button type="button" role="option" data-ticker-value="${escapeHtml(item.ticker)}"><strong>${escapeHtml(item.ticker)}</strong><span>${escapeHtml(item.company_name)}</span><small>${escapeHtml(item.sector)}</small></button>`).join('');
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
    const hasRankedSurface = Boolean(document.querySelector('[data-radar-list], [data-radar-table]'));
    const targets = document.querySelectorAll('[data-radar-list], [data-radar-table], [data-market], [data-coverage], [data-snapshot], [data-grade], [data-status]');
    if (!targets.length) return;
    try {
      const response = await fetch(siteUrl('public/data/radar.json'), { cache: 'no-store' });
      if (!response.ok) throw new Error('Không tải được dữ liệu Radar');
      const data = await response.json();
      document.querySelectorAll('[data-radar-list]').forEach(el => renderMiniRadar(el, data));
      document.querySelectorAll('[data-radar-table]').forEach(el => renderRadarTable(el, data));
      document.querySelectorAll('[data-market]').forEach(el => el.textContent = marketLabel(data.market_regime));
      document.querySelectorAll('[data-coverage]').forEach(el => el.textContent = `${data.snapshot.universe_coverage_pct}%`);
      document.querySelectorAll('[data-snapshot]').forEach(el => el.textContent = formatSnapshot(data.snapshot.as_of));
      document.querySelectorAll('[data-grade]').forEach(el => el.textContent = data.snapshot.data_grade);
      document.querySelectorAll('[data-status]').forEach(el => el.textContent = statusLabel(data.status));
      if (hasRankedSurface) {
        track('radar_view', { status: data.status, is_mock: data.is_mock });
        track('top_view', { status: data.status, is_mock: data.is_mock });
      }
    } catch (error) {
      targets.forEach(el => el.innerHTML = `<div class="empty">${error.message}</div>`);
    }
  }

  async function loadTrackRecord() {
    const target = document.querySelector('[data-track-record]');
    if (!target) return;
    try {
      const response = await fetch(siteUrl('public/data/track-record.json'), { cache: 'no-store' });
      const data = await response.json();
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
      track('track_record_view', { is_mock: data.is_mock });
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
          message.textContent = 'Biểu mẫu đang chờ kết nối backend bảo mật. Website demo chưa nhận hoặc lưu thông tin đăng ký.';
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
    if (document.body.dataset.pageKind === 'knowledge-hub') track('knowledge_view');
    if (document.body.dataset.pageKind === 'method') track('method_view', { method: document.body.dataset.method || 'unknown' });
    if (document.body.dataset.pageKind === 'email') track('email_view');
    document.querySelectorAll('.horizon-tab').forEach(el => el.addEventListener('click', () => track('horizon_change', { label: el.textContent.trim() })));
    document.querySelectorAll('[data-track-event]').forEach(el => el.addEventListener('click', () => track(el.dataset.trackEvent, { target: el.getAttribute('href') || '' })));
    loadRadar(); loadTrackRecord(); loadRecommendations(); loadDynamicStockReport();
    loadTodayChanges(); loadRecommendationJournal(); wireStockSearch(); wireForms();
  });
})();
