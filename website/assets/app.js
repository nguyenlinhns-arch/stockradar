(() => {
  const apiMode = document.documentElement.dataset.apiMode || 'auto';
  const allowedEvents = new Set([
    'ad_click', 'landing_view', 'radar_view', 'top5_expand', 'track_record_view',
    'signup_started', 'signup_completed', 'alert_opt_in', 'pro_page_view',
    'trial_started', 'subscription_started', 'return_d1', 'return_d7',
    'knowledge_view', 'method_view', 'horizon_select', 'stock_search',
    'stock_report_view', 'top10_view', 'watchlist_add', 'email_view',
    'checkout_started', 'payment_completed'
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
        ['radar5/', 'Top cổ phiếu', '/radar5'],
        ['nganh/', 'Theo ngành', '/nganh'],
        ['phan-tich/', 'Phân tích mã', '/phan-tich'],
        ['khuyen-nghi/', 'Đang hiệu lực', '/khuyen-nghi'],
        ['kien-thuc/', 'Kiến thức', '/kien-thuc'],
        ['track-record/', 'Kết quả', '/track-record'],
      ];
      menu.innerHTML = items.map(([href, label, match]) =>
        `<a href="${href}"${route.endsWith(match) || route.includes(`${match}/`) ? ' aria-current="page"' : ''}>${label}</a>`
      ).join('') + '<a class="button button-primary button-small" href="pro/">Nâng cấp</a>';
    }

    const utility = document.createElement('div');
    utility.className = 'portal-utility';
    utility.innerHTML = `
      <div class="container portal-utility-inner">
        <span><strong>STOCKRADAR RESEARCH</strong><i></i>Sàng lọc cổ phiếu HOSE theo mục tiêu</span>
        <span class="portal-utility-note">V1 kiểm chứng sản phẩm · Không phải khuyến nghị đầu tư</span>
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
      <a href="breakout/">Điểm kích hoạt</a><a href="risk/">Radar rủi ro</a>
      <a href="email/">Cảnh báo email</a><a href="theo-doi/">Mã đang theo dõi</a>
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

  function renderRecommendations(target, data) {
    target.innerHTML = `
      <div class="rec-row rec-head"><span>Mã</span><span>Kỳ hạn</span><span>Ngày KN</span><span>Vùng mua</span><span>Giá hiện tại</span><span>Mục tiêu</span><span>Cắt lỗ / quản trị</span><span>R:R</span><span>Trạng thái</span></div>
      ${data.items.map(item => `
        <article class="rec-row">
          <div>${recommendationLink(item)}<small>${item.sector}</small></div>
          <strong>${horizonLabels[item.horizon] || item.horizon}</strong>
          <span>${new Date(item.recommendation_date).toLocaleDateString('vi-VN')}</span>
          <span>${priceRange(item.recommended_buy_low, item.recommended_buy_high)}</span>
          <span>${formatPrice(item.current_price)}</span>
          <span>${formatPrice(item.target_price)}</span>
          <span>${item.stop_loss == null ? 'Theo luận điểm' : formatPrice(item.stop_loss)}</span>
          <span>${item.risk_reward == null ? '—' : `${formatPrice(item.risk_reward)}:1`}</span>
          <span><span class="state ${stateClass(item.recommendation_state)}">${stateLabel(item.recommendation_state)}</span></span>
        </article>`).join('')}`;
  }

  function renderStockReport(target, item, data) {
    const horizonTabs = Object.entries(horizonLabels).map(([value, label]) => `
      <div class="report-horizon ${value === item.horizon ? 'is-active' : ''}">
        <strong>${label}</strong><span>${value === item.horizon ? 'Record demo hiện tại' : 'Chưa có record demo'}</span>
      </div>`).join('');
    const list = values => values.map(value => `<li>${value}</li>`).join('');
    target.innerHTML = `
      <section class="report-overview">
        <div class="report-title"><div><span class="panel-label">BÁO CÁO CỔ PHIẾU · MÔ PHỎNG</span><h1>${item.ticker}</h1><p>${item.company_name} · ${item.sector}</p></div><span class="state ${stateClass(item.recommendation_state)}">${stateLabel(item.recommendation_state)}</span></div>
        <div class="report-metrics">
          <div><span>Giá hiện tại demo</span><strong>${formatPrice(item.current_price)}</strong></div>
          <div><span>Điểm StockRadar</span><strong>${formatPrice(item.stock_score)}<small>/100</small></strong></div>
          <div><span>Xếp hạng mục tiêu</span><strong>#${item.rank}</strong></div>
          <div><span>Trạng thái thị trường</span><strong>${marketLabel(item.market_regime)}</strong></div>
          <div><span>Độ phủ điểm</span><strong>${formatPrice(item.score_coverage_pct)}%</strong></div>
          <div><span>Cấp dữ liệu</span><strong>${item.data_grade}</strong></div>
        </div>
      </section>
      <div class="report-horizons">${horizonTabs}</div>
      <section class="recommendation-plan">
        <header><div><span class="panel-label">KẾ HOẠCH CÓ ĐIỀU KIỆN</span><h2>${horizonLabels[item.horizon]}</h2></div><span class="data-pill">Tất cả con số đều là MOCK</span></header>
        <div class="plan-metrics">
          <div><span>Giá mua khuyến nghị</span><strong>${priceRange(item.recommended_buy_low, item.recommended_buy_high)}</strong></div>
          <div><span>Giá tại ngày khuyến nghị</span><strong>${formatPrice(item.price_at_recommendation)}</strong></div>
          <div><span>Giá hiện tại</span><strong>${formatPrice(item.current_price)}</strong></div>
          <div><span>Mục tiêu / giá trị hợp lý</span><strong>${formatPrice(item.target_price)}</strong></div>
          <div><span>Cắt lỗ / điểm vô hiệu</span><strong>${item.stop_loss == null ? 'Theo luận điểm' : formatPrice(item.stop_loss)}</strong></div>
          <div><span>Tỷ lệ lợi nhuận/rủi ro</span><strong>${item.risk_reward == null ? 'Không áp dụng máy móc' : `${formatPrice(item.risk_reward)}:1`}</strong></div>
        </div>
      </section>
      <section class="three-questions">
        <article><span>01</span><h2>Vì sao được chọn?</h2><ul>${list(item.thesis)}</ul></article>
        <article class="is-risk"><span>02</span><h2>Rủi ro chính là gì?</h2><ul>${list(item.risks)}</ul></article>
        <article class="is-change"><span>03</span><h2>Điều gì làm nhận định thay đổi?</h2><ul>${list(item.invalidation_conditions)}</ul></article>
      </section>
      <footer class="report-audit"><span>Recommendation ID <strong>${item.recommendation_id}</strong></span><span>Snapshot <strong>${item.snapshot_id}</strong></span><span>Cập nhật <strong>${formatSnapshot(data.snapshot.as_of)}</strong></span></footer>`;
  }

  async function loadRecommendations() {
    const tables = document.querySelectorAll('[data-recommendations]');
    const reports = document.querySelectorAll('[data-stock-report]');
    if (!tables.length && !reports.length) return;
    try {
      const response = await fetch(siteUrl('public/data/recommendations.json'), { cache: 'no-store' });
      if (!response.ok) throw new Error('Không tải được dữ liệu khuyến nghị');
      const data = await response.json();
      tables.forEach(target => renderRecommendations(target, data));
      reports.forEach(target => {
        const ticker = String(target.dataset.stockReport || '').toUpperCase();
        const item = data.items.find(record => record.ticker === ticker);
        target.innerHTML = item ? '' : '<div class="empty">Chưa có báo cáo mô phỏng cho mã này.</div>';
        if (item) renderStockReport(target, item, data);
      });
      if (reports.length) track('stock_report_view', { ticker: reports[0].dataset.stockReport || '', is_mock: data.is_mock });
    } catch (error) {
      [...tables, ...reports].forEach(target => target.innerHTML = `<div class="empty">${error.message}</div>`);
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
          result.innerHTML = '<strong>Đã có báo cáo mẫu DEMO1.</strong><span>Báo cáo minh hoạ đủ bốn lớp: dữ liệu, vùng giá, luận điểm và rủi ro.</span><a class="button button-primary button-small" href="co-phieu/demo1/">Mở báo cáo mẫu</a>';
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
      track('radar_view', { status: data.status, is_mock: data.is_mock });
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
        if (!started) { started = true; track('signup_started'); }
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
    if (/(^|\/)pro\/?$/.test(location.pathname)) track('pro_page_view');
    if (document.body.dataset.pageKind === 'knowledge-hub') track('knowledge_view');
    if (document.body.dataset.pageKind === 'method') track('method_view', { method: document.body.dataset.method || 'unknown' });
    if (document.body.dataset.pageKind === 'email') track('email_view');
    document.querySelectorAll('[data-track-event]').forEach(el => el.addEventListener('click', () => track(el.dataset.trackEvent, { target: el.getAttribute('href') || '' })));
    loadRadar(); loadTrackRecord(); loadRecommendations(); wireStockSearch(); wireForms();
  });
})();
