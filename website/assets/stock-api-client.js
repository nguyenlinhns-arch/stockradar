(() => {
  'use strict';

  const HORIZONS = Object.freeze({
    SHORT_TERM: 'Ngắn hạn',
    MEDIUM_TERM: 'Trung hạn',
    LONG_TERM: 'Dài hạn',
    ACCUMULATION: 'Tích sản',
  });

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

  function formatNumber(value, digits = 2) {
    if (value == null || value === '' || Number.isNaN(Number(value))) return '—';
    return Number(value).toLocaleString('vi-VN', { maximumFractionDigits: digits });
  }

  function formatPercent(value) {
    if (value == null || value === '' || Number.isNaN(Number(value))) return '—';
    const number = Number(value);
    return `${number > 0 ? '+' : ''}${number.toLocaleString('vi-VN', { maximumFractionDigits: 2 })}%`;
  }

  function formatProbability(value) {
    if (value == null || value === '' || Number.isNaN(Number(value))) return '—';
    const number = Number(value);
    if (number < 0 || number > 100) return '—';
    return `${number.toLocaleString('vi-VN', { maximumFractionDigits: 2 })}%`;
  }

  function formatDateTime(value) {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '—';
    return new Intl.DateTimeFormat('vi-VN', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: false,
    }).format(date);
  }

  function priceRange(payload) {
    if (Array.isArray(payload.buy_zone) && payload.buy_zone.length >= 2) {
      return `${formatNumber(payload.buy_zone[0])}–${formatNumber(payload.buy_zone[1])}`;
    }
    const low = payload.buy_zone_low ?? payload.buy_low;
    const high = payload.buy_zone_high ?? payload.buy_high;
    return low == null || high == null ? '—' : `${formatNumber(low)}–${formatNumber(high)}`;
  }

  function textList(values) {
    const items = Array.isArray(values) ? values.filter(Boolean).slice(0, 6) : [];
    return items.length
      ? `<ul>${items.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`
      : '<p>Chưa có dữ liệu công bố cho mục này.</p>';
  }

  function renderLiveReport(container, response, selectedHorizon) {
    const payload = response.payload && typeof response.payload === 'object' ? response.payload : {};
    const ticker = response.ticker || payload.ticker || '—';
    const company = payload.company_name || payload.name || '';
    const sector = payload.sector || '';
    const assessment = payload.assessment || payload.action || payload.new_position_state || 'CHƯA CÓ KẾT LUẬN';
    const holding = payload.holding_state || 'CHƯA CÓ KẾT LUẬN';
    const calibratedProbability = payload.probability_calibrated === true && payload.probability_pct != null
      ? formatProbability(payload.probability_pct)
      : 'KHÔNG CÔNG BỐ';

    container.innerHTML = `
      <section class="live-stock-report premium-live-stock-report" aria-live="polite">
        <header class="live-report-head">
          <div><span class="panel-label">PREMIUM · ${escapeHtml(HORIZONS[selectedHorizon])}</span><h1>${escapeHtml(ticker)}</h1><p>${escapeHtml(company)}${company && sector ? ' · ' : ''}${escapeHtml(sector)}</p></div>
          <span class="data-pill">PREMIUM</span>
        </header>
        <nav class="live-horizon-tabs" aria-label="Khung đầu tư">
          ${Object.entries(HORIZONS).map(([value, label]) => `<button type="button" data-live-horizon="${value}" class="${value === selectedHorizon ? 'is-active' : ''}">${label}</button>`).join('')}
        </nav>
        <div class="live-report-status"><div><span>Mua mới</span><strong>${escapeHtml(assessment)}</strong></div><div><span>Đang nắm giữ</span><strong>${escapeHtml(holding)}</strong></div></div>
        <div class="live-report-metrics">
          <div><span>Giá hiện tại</span><strong>${formatNumber(payload.current_price)}</strong></div>
          <div><span>Setup</span><strong>${escapeHtml(payload.setup || payload.setup_type || '—')}</strong></div>
          <div><span>Điểm</span><strong>${payload.score == null ? '—' : `${formatNumber(payload.score, 1)}/100`}</strong></div>
          <div><span>RVOL</span><strong>${payload.rvol == null && payload.volume_rvol == null ? '—' : `${formatNumber(payload.rvol ?? payload.volume_rvol)}x`}</strong></div>
          <div><span>Buy Zone</span><strong>${priceRange(payload)}</strong></div>
          <div><span>Stop-loss</span><strong>${formatNumber(payload.stop_loss)}</strong></div>
          <div><span>Target gần</span><strong>${formatNumber(payload.target_near ?? payload.target_price)}</strong></div>
          <div><span>Target 3–6 tháng</span><strong>${formatNumber(payload.target_3_6m)}</strong></div>
          <div><span>Target 12 tháng</span><strong>${formatNumber(payload.target_12m ?? payload.fair_value)}</strong></div>
          <div><span>Upside</span><strong>${formatPercent(payload.upside_pct)}</strong></div>
          <div><span>Downside</span><strong>${formatPercent(payload.downside_pct)}</strong></div>
          <div><span>Risk/Reward</span><strong>${payload.risk_reward == null ? '—' : `${formatNumber(payload.risk_reward)}:1`}</strong></div>
          <div><span>Xác suất mô hình</span><strong>${calibratedProbability}</strong></div>
          <div><span>Snapshot</span><strong>${formatDateTime(response.generated_at)}</strong></div>
        </div>
        <div class="live-report-evidence">
          <article><span class="panel-label">LUẬN ĐIỂM / CATALYST</span>${textList(payload.thesis || payload.catalysts)}</article>
          <article><span class="panel-label">RỦI RO / VÔ HIỆU</span>${textList(payload.risks || payload.invalidation_conditions)}</article>
        </div>
        <footer class="live-report-foot">Snapshot <strong>${escapeHtml(response.snapshot_id || '—')}</strong> · Hết hạn cache <strong>${formatDateTime(response.expires_at)}</strong>. Chỉ hiển thị xác suất khi payload xác nhận đã hiệu chỉnh.</footer>
      </section>`;
  }

  function renderLiveMessage(container, message) {
    container.innerHTML = `<div class="live-report-message">${escapeHtml(message)}</div>`;
  }

  async function getClientAndSession() {
    const config = window.STOCKRADAR_AUTH_CONFIG || {};
    if (!config.configured || !config.supabaseUrl || !config.supabasePublishableKey || !window.supabase?.createClient) return null;
    const client = window.StockRadarAuthClient || window.supabase.createClient(
      config.supabaseUrl,
      config.supabasePublishableKey,
      { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, storageKey: 'stockradar-auth' } },
    );
    window.StockRadarAuthClient = client;
    const { data, error } = await client.auth.getSession();
    if (error || !data?.session?.access_token) return null;
    return { client, session: data.session, config };
  }

  async function fetchReport(auth, ticker, horizon) {
    const endpoint = `${auth.config.supabaseUrl}/functions/v1/stock-api?ticker=${encodeURIComponent(ticker)}&horizon=${encodeURIComponent(horizon)}`;
    const response = await fetch(endpoint, {
      method: 'GET',
      cache: 'no-store',
      headers: {
        apikey: auth.config.supabasePublishableKey,
        Authorization: `Bearer ${auth.session.access_token}`,
      },
    });
    let payload = {};
    try { payload = await response.json(); } catch (_) { payload = {}; }
    return { response, payload };
  }

  async function mountAuthenticatedStockReport() {
    const staticTarget = document.querySelector('[data-dynamic-stock-report]');
    const premiumTarget = document.querySelector('[data-premium-stock-report]');
    const premiumGateCopy = document.querySelector('[data-premium-gate-copy]');
    const ticker = tickerFromLocation();
    if (!staticTarget || !ticker) return;

    const auth = await getClientAndSession();
    if (!auth) return;

    const requestedHorizon = String(new URLSearchParams(location.search).get('horizon') || 'SHORT_TERM').toUpperCase();
    let horizon = Object.prototype.hasOwnProperty.call(HORIZONS, requestedHorizon) ? requestedHorizon : 'SHORT_TERM';
    let liveContainer = null;

    const ensureLiveContainer = () => {
      if (liveContainer) return liveContainer;
      if (premiumTarget) {
        liveContainer = premiumTarget;
        liveContainer.hidden = false;
      } else {
        liveContainer = document.createElement('div');
        liveContainer.className = 'stock-api-live';
        liveContainer.setAttribute('data-stock-api-live', '');
        staticTarget.after(liveContainer);
      }
      if (premiumGateCopy) premiumGateCopy.hidden = true;
      return liveContainer;
    };

    const load = async nextHorizon => {
      horizon = nextHorizon;
      const { response, payload } = await fetchReport(auth, ticker, horizon);
      if (response.status === 429) {
        const container = ensureLiveContainer();
        renderLiveMessage(container, 'Đã đạt giới hạn tra cứu tạm thời. Vui lòng thử lại sau.');
        return true;
      }
      if (!response.ok || payload.status !== 'READY') return false;

      const container = ensureLiveContainer();
      renderLiveReport(container, payload, horizon);
      container.querySelectorAll('[data-live-horizon]').forEach(button => {
        button.addEventListener('click', () => load(button.dataset.liveHorizon));
      });
      history.replaceState(null, '', `${location.pathname}?ticker=${encodeURIComponent(ticker)}&horizon=${encodeURIComponent(horizon)}`);
      return true;
    };

    try { await load(horizon); } catch (_) { /* Keep Free and Premium-gate surfaces fail closed. */ }
  }

  document.addEventListener('DOMContentLoaded', mountAuthenticatedStockReport);
})();