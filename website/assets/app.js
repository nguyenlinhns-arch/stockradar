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
        ['radar5/', 'Cổ phiếu nổi bật', '/radar5'],
        ['nganh/', 'Theo ngành', '/nganh'],
        ['khuyen-nghi/', 'Khuyến nghị', '/khuyen-nghi'],
        ['phan-tich/', 'Phân tích cổ phiếu', '/phan-tich'],
        ['hieu-qua/', 'Hiệu quả', '/hieu-qua'],
        ['tai-khoan/', 'Tài khoản', '/tai-khoan'],
      ];
      menu.innerHTML = items.map(([href, label, match]) => {
        const isCurrent = route.endsWith(match)
          || route.includes(`${match}/`)
          || (match === '/phan-tich' && route.includes('/co-phieu/'));
        return `<a href="${href}"${isCurrent ? ' aria-current="page"' : ''}>${label}</a>`;
      }).join('') + '<a class="button button-primary button-small" href="pro/">Nâng cấp</a>';
    }

    const utility = document.createElement('div');
    utility.className = 'portal-utility';
    utility.innerHTML = `
      <div class="container portal-utility-inner">
        <span><strong>STOCKRADAR RESEARCH</strong><i></i>Xếp hạng nghiên cứu theo bốn mục tiêu</span>
        <span class="portal-utility-note">V2 · RESEARCH_ONLY · Không phải khuyến nghị đầu tư</span>
      </div>`;

    const tape = document.createElement('section');
    tape.className = 'market-tape';
    tape.setAttribute('aria-label', 'Trạng thái dữ liệu StockRadar');
    tape.innerHTML = `
      <div class="container market-tape-inner" aria-live="polite">
        <div class="tape-heading"><span class="live-dot" aria-hidden="true"></span><span>RADAR SNAPSHOT</span><strong>MÔ PHỎNG</strong></div>
        <div class="tape-item"><span>Trạng thái demo</span><strong data-market>—</strong></div>
        <div class="tape-item"><span>Độ phủ fixture</span><strong data-coverage>—</strong></div>
        <div class="tape-item tape-snapshot"><span>Cập nhật</span><strong data-snapshot>—</strong></div>
        <div class="tape-disclaimer">Chưa kết nối dữ liệu thị trường thật</div>
      </div>`;

    const subnav = document.createElement('nav');
    subnav.className = 'product-subnav';
    subnav.setAttribute('aria-label', 'Điều hướng phân tích');
    subnav.innerHTML = `<div class="container product-subnav-inner">
      <a href="radar5/">Ngắn hạn</a><a href="kien-thuc/#trung-han">Trung hạn</a>
      <a href="kien-thuc/#dai-han">Dài hạn</a><a href="kien-thuc/#tich-san">Tích sản</a>
      <a href="kien-thuc/">Kiến thức</a><a href="track-record/">Nhật ký công bố</a>
      <a href="email/">Email trước phiên</a><a href="theo-doi/">Mã đang theo dõi</a>
    </div>`;

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
    if (item.ticker === 'DEMO1') return `<a class="table-ticker ticker-link" href="co-phieu/demo1/">${item.ticker}</a>`;
    return `<span class="table-ticker">${item.ticker}</span>`;
  }

  function renderRecommendations(target, data, filter = 'ALL') {
    const items = data.items.filter(item => filter === 'ALL' || lifecycleGroup(item) === filter);
    target.innerHTML = `
      <div class="rec-row rec-head"><span>Mã</span><span>Kỳ hạn</span><span>Công bố</span><span>Kích hoạt</span><span>Vùng mua</span><span>Entry hiệu quả</span><span>Giá hiện tại / đóng</span><span>Lãi / lỗ</span><span>Mục tiêu</span><span>Rủi ro</span><span>Trạng thái</span></div>
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
        <span>${formatPercent(item.benchmark_return_pct)}</span>
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
        return `<a href="${item.ticker === 'DEMO1' ? 'co-phieu/demo1/' : 'khuyen-nghi/'}"><span><strong>${item.ticker}</strong><small>${horizonLabels[item.horizon]}</small></span><span class="state ${stateClass(item.recommendation_state)}">${stateLabel(item.recommendation_state)}</span><b class="${returnClass(performance.value)}">${performance.label}</b></a>`;
      }).join('')}</div>
      <small class="home-proof-note">* Chỉ tính record đã đóng; loại record chưa kích hoạt. Toàn bộ là MOCK/SHADOW.</small>`;
  }

  function renderStockReport(target, item, data) {
    const horizonTabs = Object.entries(horizonLabels).map(([value, label]) => `
      <div class="report-horizon ${value === item.horizon ? 'is-active' : ''}">
        <strong>${label}</strong><span>${value === item.horizon ? 'Record demo hiện tại' : 'Chưa có record demo'}</span>
      </div>`).join('');
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
        </div>
      </section>
      <section class="report-answers" aria-label="Chín câu hỏi của báo cáo StockRadar">
        <article><span>01 · ĐÁNH GIÁ</span><h2>Đánh giá hiện tại?</h2><p>${stateLabel(item.recommendation_state)}. ${resultText}</p></article>
        <article><span>02 · XẾP HẠNG</span><h2>Đứng ở đâu trong mục tiêu?</h2><p>Hạng #${item.rank} của mô hình ${horizonLabels[item.horizon]}, điểm ${formatPrice(item.stock_score)}/100 với độ phủ ${formatPrice(item.score_coverage_pct)}%.</p></article>
        <article><span>03 · VỊ TRÍ GIÁ</span><h2>Giá đang ở đâu?</h2><p>${pricePosition(item)}</p></article>
        <article><span>04 · HÀNH ĐỘNG</span><h2>Vùng mua và entry?</h2><p>Vùng ${priceRange(item.recommended_buy_low, item.recommended_buy_high)}. ${activationText}</p></article>
        <article><span>05 · MỤC TIÊU</span><h2>Mốc nào cần theo dõi?</h2><p>Mục tiêu ${formatPrice(item.target_price)}; ${item.stop_loss == null ? 'điểm vô hiệu theo thay đổi luận điểm.' : `mức quản trị ${formatPrice(item.stop_loss)}.`}</p></article>
        <article><span>06 · LUẬN ĐIỂM</span><h2>Vì sao được chọn?</h2><ul>${list(item.thesis)}</ul></article>
        <article class="is-risk"><span>07 · RỦI RO</span><h2>Rủi ro chính là gì?</h2><ul>${list(item.risks)}</ul></article>
        <article class="is-change"><span>08 · VÔ HIỆU</span><h2>Điều gì làm nhận định đổi?</h2><ul>${list(item.invalidation_conditions)}</ul></article>
        <article><span>09 · LỊCH SỬ</span><h2>Record trước được lưu thế nào?</h2><p>${resultText} Benchmark ${formatPercent(item.benchmark_return_pct)}; vượt chuẩn ${formatPercent(item.excess_return_pct)}.</p></article>
      </section>
      <footer class="report-audit"><span>Recommendation ID <strong>${item.recommendation_id}</strong></span><span>Snapshot <strong>${item.snapshot_id}</strong></span><span>System <strong>${item.system_version}</strong></span><span>Score model <strong>${item.score_version}</strong></span><span>Adjustment <strong>${item.adjustment_basis}</strong></span><span>Cập nhật <strong>${formatSnapshot(data.snapshot.as_of)}</strong></span></footer>`;
  }

  async function loadRecommendations() {
    const tables = document.querySelectorAll('[data-recommendations]');
    const reports = document.querySelectorAll('[data-stock-report]');
    const performanceTargets = document.querySelectorAll('[data-performance-summary]');
    const performanceMiniTargets = document.querySelectorAll('[data-performance-mini]');
    if (!tables.length && !reports.length && !performanceTargets.length && !performanceMiniTargets.length) return;
    try {
      const response = await fetch(siteUrl('public/data/recommendations.json'), { cache: 'no-store' });
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
        if (item) renderStockReport(target, item, data);
      });
      performanceTargets.forEach(target => renderPerformance(target, data));
      performanceMiniTargets.forEach(target => renderPerformanceMini(target, data));
      if (tables.length) track('recommendation_list_view', { is_mock: data.is_mock, record_mode: data.items[0]?.record_mode });
      if (reports.length) {
        track('stock_report_view', { ticker: reports[0].dataset.stockReport || '', is_mock: data.is_mock });
        track('sample_premium_report_view', { ticker: reports[0].dataset.stockReport || '', is_mock: data.is_mock });
      }
      if (performanceTargets.length) track('performance_view', { is_mock: data.is_mock, total_published: data.performance_summary.total_published });
    } catch (error) {
      [...tables, ...reports, ...performanceTargets, ...performanceMiniTargets].forEach(target => target.innerHTML = `<div class="empty">${error.message}</div>`);
    }
  }

  function wireStockSearch() {
    document.querySelectorAll('[data-stock-search-form]').forEach(form => {
      const result = form.parentElement.querySelector('[data-stock-search-result]');
      const input = form.querySelector('input[name="ticker"]');
      const show = value => {
        const ticker = String(value || '').trim().toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 12);
        if (!ticker) return;
        track('stock_search', { ticker });
        if (ticker === 'DEMO1') {
          result.className = 'search-result is-available';
          result.innerHTML = '<strong>Đã có báo cáo mẫu DEMO1.</strong><span>Báo cáo trả lời chín câu hỏi từ xếp hạng, vùng mua, activation đến lịch sử hiệu quả.</span><a class="button button-primary button-small" href="co-phieu/demo1/">Mở báo cáo mẫu</a>';
        } else {
          result.className = 'search-result is-unavailable';
          result.innerHTML = `<strong>${ticker}: chưa có dữ liệu thị trường thật.</strong><span>StockRadar không tự dựng giá, điểm hay khuyến nghị cho mã chưa có snapshot đạt chuẩn.</span><a href="co-phieu/demo1/">Xem cấu trúc báo cáo DEMO1 →</a>`;
        }
      };
      form.addEventListener('submit', event => { event.preventDefault(); show(input.value); });
      const preset = new URLSearchParams(location.search).get('ticker');
      if (preset) { input.value = preset; show(preset); }
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
      let started = false;
      form.addEventListener('input', () => {
        if (!started) { started = true; track('signup_started'); track('signup_start'); }
      }, { once: true });
      form.addEventListener('submit', async event => {
        event.preventDefault();
        const message = form.querySelector('[data-form-message]');
        const data = Object.fromEntries(new FormData(form).entries());
        data.consent = form.querySelector('[name="consent"]')?.checked || false;
        data.alert_opt_in = form.querySelector('[name="alert_opt_in"]')?.checked || false;
        data.utm = getUtm();
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
    loadRadar(); loadTrackRecord(); loadRecommendations(); wireStockSearch(); wireForms();
  });
})();
