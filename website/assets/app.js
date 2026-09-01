(() => {
  const apiMode = document.documentElement.dataset.apiMode || 'auto';
  const allowedEvents = new Set([
    'ad_click', 'landing_view', 'radar_view', 'top5_expand', 'track_record_view',
    'signup_started', 'signup_completed', 'alert_opt_in', 'pro_page_view',
    'trial_started', 'subscription_started', 'return_d1', 'return_d7',
    'knowledge_view', 'method_view', 'horizon_select'
  ]);

  const stateLabels = {
    WATCH: 'THEO DÕI',
    NEAR_TRIGGER: 'GẦN KÍCH HOẠT',
    READY: 'SẴN SÀNG',
    TRIGGERED: 'ĐÃ KÍCH HOẠT',
    INVALIDATED: 'MẤT HIỆU LỰC',
    EXTENDED: 'KÉO GIÃN',
    EXPIRED: 'HẾT HẠN',
    UNCHANGED: 'KHÔNG ĐỔI'
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

  function mountPortalShell() {
    const header = document.querySelector('.site-header');
    if (!header || document.querySelector('.portal-utility')) return;

    const menu = header.querySelector('[data-nav-menu]');
    if (menu) {
      const route = location.pathname.replace(/\/+$/, '');
      const items = [
        ['radar5/', 'Radar cổ phiếu', '/radar5'],
        ['breakout/', 'Điểm kích hoạt', '/breakout'],
        ['risk/', 'Cảnh báo', '/risk'],
        ['kien-thuc/', 'Kiến thức', '/kien-thuc'],
        ['track-record/', 'Kết quả', '/track-record'],
        ['pro/', 'Gói PRO', '/pro']
      ];
      menu.innerHTML = items.map(([href, label, match]) =>
        `<a href="${href}"${route.endsWith(match) || route.includes(`${match}/`) ? ' aria-current="page"' : ''}>${label}</a>`
      ).join('') + '<a class="button button-primary button-small" href="radar5/">Mở Radar</a>';
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

    header.before(utility);
    header.after(tape);
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
          <div><div class="table-ticker">${item.ticker}</div><div class="setup">${item.setup} · ${item.reason}</div></div>
          <strong class="score">${item.score}</strong>
          <span><span class="state ${stateClass(item.state)}">${stateLabel(item.state)}</span></span>
          <span class="demo-price">${Number(item.current_price).toLocaleString('vi-VN')}</span>
          <span class="pivot-distance">${Number(item.distance_to_pivot_pct).toLocaleString('vi-VN')}%</span>
          <span class="change ${item.state_change === 'UNCHANGED' ? 'unchanged' : ''}">${item.state_change === 'UNCHANGED' ? stateLabel(item.state_change) : item.state_change.split('→').map(stateLabel).join(' → ')}</span>
        </article>`).join('')}`;
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
    document.querySelectorAll('[data-track-event]').forEach(el => el.addEventListener('click', () => track(el.dataset.trackEvent, { target: el.getAttribute('href') || '' })));
    loadRadar(); loadTrackRecord(); wireForms();
  });
})();
