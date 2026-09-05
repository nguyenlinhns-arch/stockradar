(() => {
  'use strict';

  const DATA = {
    radar: 'public/data/radar.json',
    recommendations: 'public/data/recommendations.json',
    today: 'public/data/today-changes.json',
  };

  function qs(selector) { return document.querySelector(selector); }
  function setText(selector, value) { const el = qs(selector); if (el) el.textContent = value; }
  function text(value, fallback = '—') { const valueText = value == null ? '' : String(value).trim(); return valueText || fallback; }
  function number(value, fallback = '—') { if (value == null || value === '' || typeof value === 'boolean') return fallback; const n = Number(value); return Number.isFinite(n) ? new Intl.NumberFormat('vi-VN').format(n) : fallback; }
  function pct(value, fallback = '—') { if (value == null || value === '' || typeof value === 'boolean') return fallback; const n = Number(value); return Number.isFinite(n) ? `${n.toLocaleString('vi-VN', { maximumFractionDigits: 1 })}%` : fallback; }

  function fmtTime(value) {
    if (!value) return 'Chưa ghi nhận';
    try {
      return new Intl.DateTimeFormat('vi-VN', {
        timeZone: 'Asia/Ho_Chi_Minh',
        year: 'numeric', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
      }).format(new Date(value));
    } catch (_) {
      return text(value);
    }
  }

  function isBlocked(payload) {
    const status = String(payload?.data_status || payload?.status || '').trim().toUpperCase();
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

  function rangeValue(value) {
    if (Array.isArray(value) && value.length >= 2) return `${number(value[0])}–${number(value[1])}`;
    if (value && typeof value === 'object') {
      const low = value.low ?? value.min ?? value.from;
      const high = value.high ?? value.max ?? value.to;
      if (low != null || high != null) return `${number(low)}–${number(high)}`;
    }
    return text(value);
  }

  function normalizeHeaderActions() {
    const href = new URL('dang-ky/?plan=free', document.baseURI).toString();
    document.querySelectorAll('.header-register-cta').forEach(link => {
      link.href = href;
      link.textContent = 'Đăng ký Free';
      link.setAttribute('aria-label', 'Mở trang đăng ký StockRadar Free');
    });
  }

  async function recommendationStatus() {
    const c = window.STOCKRADAR_AUTH_CONFIG || {};
    const response = await fetch(`${c.supabaseUrl}/rest/v1/rpc/get_stockradar_recommendation_status_v1`, {
      method:'POST', headers:{apikey:c.supabasePublishableKey,'Content-Type':'application/json'}, body:'{}', cache:'no-store', signal:AbortSignal.timeout(12000)
    });
    if (!response.ok) throw new Error('Recommendation status unavailable');
    const value = await response.json();
    if (value.schema_version !== 'STOCKRADAR_RECOMMENDATION_STATUS_V1') throw new Error('Invalid recommendation status');
    return value;
  }

  function renderSchedule(payload) {
    const s=payload?.snapshot || {}, email=payload?.email || {}, schedule=payload?.schedule || {};
    const date=String(s.as_of_date || '').match(/^(\d{4})-(\d{2})-(\d{2})$/);
    setText('[data-reco-price-date]',date ? `${date[3]}/${date[2]}/${date[1]}` : 'Chưa ghi nhận');
    setText('[data-reco-reviewed-at]',fmtTime(s.evaluated_at));
    setText('[data-reco-next-review]',fmtTime(schedule.next_review_at));
    setText('[data-reco-email-state]',email.status==='DOMAIN_UNVERIFIED' ? 'Chưa gửi · chờ xác minh tên miền' : email.ready ? 'Đã bật kênh gửi' : 'Chưa bật gửi');
    if (schedule.next_daily_planned_at) setText('[data-reco-email-schedule]',`Lịch thường lệ thứ Hai–thứ Sáu: bản tin tiếp theo dự kiến ${fmtTime(schedule.next_daily_planned_at)}; kiểm tra cảnh báo ${schedule.alert_checkpoints.join(' · ')} (giờ VN). ${email.ready ? 'Chỉ gửi khi đủ điều kiện và đã bật nhận email; thời gian xử lý có thể chậm hơn lịch.' : 'Chưa có lịch gửi thực tế vì kênh email chưa được kích hoạt.'}`);
  }

  function renderRecommendations(payload) {
    const body = qs('[data-home-reco-body]');
    const empty = qs('[data-home-reco-empty]');
    const table = qs('[data-home-reco-table]');
    if (!body || !empty || !table) return;

    const items = Array.isArray(payload?.items) ? payload.items.filter(x => x.publish_status === 'PUBLISHED' && x.action === 'MUA' && Date.parse(x.expires_at) > Date.now()) : [];
    renderSchedule(payload);
    const ready = payload?.data_status === 'READY' && items.length > 0;
    body.replaceChildren();

    if (!ready) {
      table.hidden = true;
      empty.hidden = false;
      const coverage=payload?.coverage || {}, status=payload?.data_status;
      empty.querySelector('strong').textContent = status==='NO_QUALIFIED_BUYS' ? `Chưa có mã đủ điều kiện mua · đã rà soát ${number(coverage.reviewed)} mã HOSE` : status==='STALE' ? 'Dữ liệu rà soát đã cũ · chờ cập nhật' : status==='PUBLICATION_PENDING' ? 'Chưa có khuyến nghị được xác nhận để công bố' : 'Chưa tải được kết quả rà soát';
      setText('[data-home-reco-reason]',status==='NO_QUALIFIED_BUYS' ? `${number(coverage.initial_setups)} mã có dấu hiệu giá/khối lượng ban đầu, nhưng chưa đáp ứng đầy đủ tiêu chí mua.` : 'Chưa đủ cơ sở để xác nhận danh sách mua mới.');
      setText('[data-home-reco-state]',payload?.checked_at ? `Kiểm tra trạng thái lúc ${fmtTime(payload.checked_at)} · giờ Việt Nam` : 'Không thể xác nhận trạng thái hiện tại; vui lòng tải lại.');
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
        number(item?.reference_price),
        rangeValue(item.buy_zone),
        number(item.stop_loss),
        number(item.target),
        `${number(item.risk_reward)} lần`,
        fmtTime(item.confirmed_at),
        item.email_status==='SENT' ? `Đã gửi: ${fmtTime(item.email_sent_at)}` : item.email_status==='QUEUED' ? `Chờ gửi: ${fmtTime(item.email_scheduled_at)}` : item.email_status==='DISABLED' ? 'Kênh gửi chưa bật' : 'Chưa có email được xếp lịch',
      ];

      values.forEach((value, index) => {
        const td = document.createElement('td');
        if (index === 0) td.className = 'reco-ticker';
        if (index === 0) {
          const link=document.createElement('a'); link.href=`co-phieu/?ticker=${encodeURIComponent(ticker)}`; link.textContent=value; td.append(link);
        } else if (index === 1) {
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

    setText('[data-home-reco-state]', `${Math.min(5, items.length)} mã được xác nhận mua · giờ Việt Nam.`);
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
      ? `${actionCount} thay đổi đáng chú ý trong dữ liệu hiện tại.`
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
    setTimeout(normalizeHeaderActions, 0);
    setTimeout(normalizeHeaderActions, 300);
    setTimeout(normalizeHeaderActions, 1200);

    const results = await Promise.allSettled([
      getJson(DATA.radar), getJson(DATA.recommendations), getJson(DATA.today), recommendationStatus(),
    ]);
    const radar = results[0].status === 'fulfilled' ? results[0].value : {};
    const recommendations = results[1].status === 'fulfilled' ? results[1].value : {};
    const today = results[2].status === 'fulfilled' ? results[2].value : {};

    renderMarket(radar);
    renderRecommendations(results[3].status === 'fulfilled' ? results[3].value : null);
    renderToday(today, recommendations);
    renderPerformance(recommendations);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
