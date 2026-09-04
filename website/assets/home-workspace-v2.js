(() => {
  'use strict';

  const DATA = {
    radar: 'public/data/radar.json',
    recommendations: 'public/data/recommendations.json',
    today: 'public/data/today-changes.json',
  };

  function qs(selector) { return document.querySelector(selector); }
  function setText(selector, value) { const el = qs(selector); if (el) el.textContent = value; }
  function text(value, fallback = '—') { const v = value == null ? '' : String(value).trim(); return v || fallback; }
  function number(value, fallback = '—') { const n = Number(value); return Number.isFinite(n) ? new Intl.NumberFormat('vi-VN').format(n) : fallback; }
  function pct(value, fallback = '—') { const n = Number(value); return Number.isFinite(n) ? `${n.toLocaleString('vi-VN', { maximumFractionDigits: 1 })}%` : fallback; }

  function fmtTime(value) {
    if (!value) return 'Chưa có snapshot mới';
    try {
      return new Intl.DateTimeFormat('vi-VN', {
        timeZone: 'Asia/Ho_Chi_Minh', day: '2-digit', month: '2-digit',
        hour: '2-digit', minute: '2-digit', hour12: false,
      }).format(new Date(value));
    } catch (_) { return text(value); }
  }

  function isBlocked(payload) {
    const status = String(payload?.data_status || payload?.status || '').toUpperCase();
    return !status || status.startsWith('BLOCKED');
  }

  async function getJson(path) {
    const url = new URL(path, document.baseURI);
    const response = await fetch(url, { cache: 'no-store', credentials: 'same-origin' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  function actionClass(action) {
    const value = String(action || '').toUpperCase();
    if (/MUA|BUY|NHỒI|NHOI|TĂNG|TANG/.test(value)) return 'is-buy';
    if (/BÁN|BAN|SELL|CẮT|CAT|GIẢM|GIAM/.test(value)) return 'is-sell';
    return '';
  }

  function readAction(item) {
    return text(item?.action || item?.decision || item?.state || item?.recommendation || 'CHỜ');
  }

  function readPrice(item) {
    return number(item?.reference_price ?? item?.price ?? item?.current_price ?? item?.close);
  }

  function rangeValue(value) {
    if (Array.isArray(value) && value.length >= 2) return `${number(value[0])}–${number(value[1])}`;
    if (value && typeof value === 'object') {
      const low = value.low ?? value.min ?? value.from;
      const high = value.high ?? value.max ?? value.to;
      if (low != null || high != null) return `${number(low)}–${number(high)}`;
    }
    return text(value);
  }

  function renderRecommendations(payload) {
    const body = qs('[data-home-reco-body]');
    const empty = qs('[data-home-reco-empty]');
    const table = qs('[data-home-reco-table]');
    if (!body || !empty || !table) return;

    const items = Array.isArray(payload?.items) ? payload.items : [];
    const ready = !isBlocked(payload) && items.length > 0;
    body.replaceChildren();

    if (!ready) {
      table.hidden = true;
      empty.hidden = false;
      setText('[data-home-reco-state]', 'Chưa có cổ phiếu đạt điều kiện phát hành ở snapshot hiện tại.');
      return;
    }

    table.hidden = false;
    empty.hidden = true;
    items.slice(0, 5).forEach(item => {
      const tr = document.createElement('tr');
      const ticker = text(item?.ticker || item?.symbol);
      const action = readAction(item);
      const values = [
        ticker,
        action,
        readPrice(item),
        rangeValue(item?.buy_zone ?? item?.entry_zone),
        number(item?.stop_loss ?? item?.stop ?? item?.invalidation_price),
        number(item?.target_near ?? item?.target ?? item?.target_price),
        text(item?.risk_reward ?? item?.rr ?? item?.risk_reward_ratio),
      ];
      values.forEach((value, index) => {
        const td = document.createElement('td');
        if (index === 0) td.className = 'reco-ticker';
        if (index === 1) {
          const badge = document.createElement('span');
          badge.className = `reco-action ${actionClass(action)}`.trim();
          badge.textContent = value;
          td.append(badge);
        } else {
          td.textContent = value;
        }
        tr.append(td);
      });
      body.append(tr);
    });
    setText('[data-home-reco-state]', `Đang hiển thị ${Math.min(5, items.length)} mã đã được phát hành theo dữ liệu hiện có.`);
  }

  function renderToday(today, recommendations) {
    const items = Array.isArray(today?.items) ? today.items : [];
    const ready = !isBlocked(today);
    const actionCount = ready ? items.length : 0;
    const sellCount = ready ? items.filter(item => /BÁN|BAN|SELL|CẮT|CAT|GIẢM|GIAM/i.test(readAction(item))).length : 0;
    const published = Number(recommendations?.performance_summary?.total_published || 0);

    setText('[data-today-actions]', number(actionCount, '0'));
    setText('[data-today-sells]', number(sellCount, '0'));
    setText('[data-today-published]', number(published, '0'));
    setText('[data-today-data]', ready ? 'ĐÃ CÓ' : 'CHỜ');
    setText('[data-today-note]', ready && actionCount > 0
      ? `${actionCount} thay đổi đáng chú ý trong feed hiện tại.`
      : 'Chưa có tín hiệu hành động mới được phát hành.');
    setText('[data-today-asof]', fmtTime(today?.as_of || recommendations?.snapshot?.as_of));
  }

  function renderMarket(radar) {
    const blocked = isBlocked(radar);
    const regime = String(radar?.market_regime || '').trim().toUpperCase();
    const status = blocked ? 'Chưa xác nhận' : (regime && regime !== 'UNKNOWN' ? regime : 'Đang theo dõi');
    const snapshot = radar?.snapshot || {};
    const items = Array.isArray(radar?.items) ? radar.items : [];

    setText('[data-market-status]', status);
    setText('[data-market-updated]', fmtTime(snapshot?.as_of));
    setText('[data-market-coverage]', blocked ? 'HOSE · chờ dữ liệu đủ chuẩn' : `HOSE · ${items.length} mã trong Radar`);
    const dot = qs('[data-market-dot]');
    if (dot) dot.className = `market-dot ${blocked ? 'is-warn' : 'is-ready'}`;
  }

  function renderPerformance(payload) {
    const summary = payload?.performance_summary || {};
    setText('[data-proof-total]', number(summary.total_published, '0'));
    setText('[data-proof-open]', number(summary.open, '0'));
    setText('[data-proof-closed]', number(summary.closed, '0'));
    setText('[data-proof-return]', pct(summary.average_closed_return_pct));
  }

  async function mount() {
    const results = await Promise.allSettled([
      getJson(DATA.radar), getJson(DATA.recommendations), getJson(DATA.today),
    ]);
    const radar = results[0].status === 'fulfilled' ? results[0].value : {};
    const recommendations = results[1].status === 'fulfilled' ? results[1].value : {};
    const today = results[2].status === 'fulfilled' ? results[2].value : {};

    renderMarket(radar);
    renderRecommendations(recommendations);
    renderToday(today, recommendations);
    renderPerformance(recommendations);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
