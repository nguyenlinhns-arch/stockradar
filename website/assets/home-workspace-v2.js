(() => {
  'use strict';

  const DATA = {
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
      empty.querySelector('strong').textContent = status==='NO_QUALIFIED_BUYS' ? `Chưa có điểm mua mới ở lần quét này · ${number(coverage.reviewed)} mã HOSE` : status==='STALE' ? 'Dữ liệu rà soát đã cũ · chờ cập nhật' : status==='PUBLICATION_PENDING' ? 'Chưa có khuyến nghị được xác nhận để công bố' : 'Chưa tải được kết quả rà soát';
      setText('[data-home-reco-reason]',status==='NO_QUALIFIED_BUYS' ? `${number(coverage.initial_setups)} mã có dấu hiệu giá/khối lượng ban đầu, nhưng chưa đáp ứng đầy đủ tiêu chí mua.` : 'Chưa đủ cơ sở để xác nhận danh sách mua mới.');
      setText('[data-home-reco-state]',payload?.checked_at ? `Kiểm tra trạng thái lúc ${fmtTime(payload.checked_at)} · giờ Việt Nam` : 'Không thể xác nhận trạng thái hiện tại; vui lòng tải lại.');
      return;
    }

    table.hidden = false;
    empty.hidden = true;
    items.slice(0, 3).forEach(item => {
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

    setText('[data-home-reco-state]', `${Math.min(3, items.length)} mã được xác nhận mua · giờ Việt Nam.`);
  }

  function renderToday(today, recommendations) {
    const items = Array.isArray(today?.items) ? today.items : [];
    const ready = !isBlocked(today);
    const actionCount = ready ? items.length : 0;
    const sellCount = ready ? items.filter(item => /BÁN|BAN|SELL|CẮT|CAT|GIẢM|GIAM/i.test(readAction(item))).length : 0;
    const published = Number(recommendations?.performance_summary?.total_published || 0);

    setText('[data-today-actions]', ready?number(actionCount):'—');
    setText('[data-today-sells]', ready?number(sellCount):'—');
    setText('[data-today-published]', number(published, '0'));
    setText('[data-today-data]', ready ? 'ĐÃ CÓ' : 'CHỜ');
    setText('[data-today-note]', ready && actionCount > 0
      ? `${actionCount} thay đổi đáng chú ý trong dữ liệu hiện tại.`
      : 'Chưa có tín hiệu hành động mới được phát hành.');
    setText('[data-today-asof]', fmtTime(today?.as_of || recommendations?.snapshot?.as_of));
  }

  function renderMarket(payload) {
    const snapshot=payload?.snapshot||{},at=Date.parse(snapshot.evaluated_at),now=Date.now();
    const day=Date.parse(snapshot.as_of_date),today=Date.parse(new Date(now+7*3600000).toISOString().slice(0,10));
    const fresh=snapshot.fresh===true&&Number.isFinite(at)&&at<=now+300000&&now-at<=96*3600000&&day<=today&&today-day<=96*3600000;
    setText('[data-market-status]',fresh?'RESEARCH · giá cuối phiên':'UNAVAILABLE');
    setText('[data-market-updated]',fresh?`Đóng cửa ${String(snapshot.as_of_date).split('-').reverse().join('/')}`:'Dữ liệu intraday hiện chưa khả dụng');
    setText('[data-market-reviewed]',fresh?fmtTime(snapshot.evaluated_at):'Chưa xác minh');
    setText('[data-market-coverage]',fresh?`${number(payload.coverage?.reviewed)} mã · nguồn còn hạn`:'Chưa đủ dữ liệu mới');
    setText('[data-market-intraday]','Dữ liệu intraday hiện chưa khả dụng');
    const dot = qs('[data-market-dot]');
    if (dot) dot.className = `market-dot ${fresh ? 'is-ready' : 'is-warn'}`;
  }

  function renderPerformance(payload) {
    if(payload?.schema_version!=='STOCKRADAR_VERIFIED_HISTORY_V1')return;
    const s=payload.summary;
    setText('[data-proof-total]',number(s.tickers));
    setText('[data-proof-open]',number(s.without_sell_email));
    setText('[data-proof-closed]',number(s.with_sell_email));
    setText('[data-proof-return]',pct(s.realized_return_pct));
    const box=qs('[data-home-history]');
    if(!box)return;
    box.replaceChildren();
    const a=document.createElement('a');a.href='hieu-qua/';a.textContent=`Lịch sử email đã đối chiếu: ${number(s.tickers)} mã · đến ${String(payload.mail_search_through||'').split('-').reverse().join('/')} →`;box.append(a);
    const note=document.createElement('p');note.textContent='Lịch sử email cũ được trình bày riêng, không cộng vào hiệu quả của tín hiệu production mới.';box.append(note);
  }

  function renderLiveSignals(payload) {
    const box=qs('[data-home-live-signals]');if(!box)return;
    box.replaceChildren();
    const items=payload?.is_mock===false && payload?.data_status==='READY' && Array.isArray(payload.items)
      ?payload.items.filter(r=>r.record_mode==='LIVE_PUBLISHED'&&r.publish_status==='PUBLISHED'&&r.is_mock===false&&r.data_grade==='DECISION_GRADE'&&Number.isFinite(Date.parse(r.published_at))) : [];
    const recent=[...items].sort((a,b)=>Date.parse(b.published_at)-Date.parse(a.published_at)).slice(0,3);
    box.hidden=!recent.length;
    for(const r of recent){const card=document.createElement('article');const title=document.createElement('h3');title.textContent=r.ticker;card.append(title);
      for(const value of [`${r.setup||r.recommendation_state} · ${fmtTime(r.published_at)}`,`Giá tín hiệu ${number(r.price_at_publication)}đ · Stop ${number(r.stop_loss)}đ · Target ${number(r.target_price)}đ`,
        `Trạng thái ${r.recommendation_state} · ${r.final_return_pct!=null?pct(r.final_return_pct):r.current_return_pct!=null?pct(r.current_return_pct):'Chưa kích hoạt'} · Giá đo ${fmtTime(r.close_timestamp||r.price_updated_at)}`]){const p=document.createElement('p');p.textContent=value;card.append(p);}box.append(card);}
  }

  async function mount() {
    setTimeout(normalizeHeaderActions, 0);
    setTimeout(normalizeHeaderActions, 300);
    setTimeout(normalizeHeaderActions, 1200);

    const results = await Promise.allSettled([
      getJson(DATA.recommendations).then(data=>{renderLiveSignals(data);return data;}), (qs('[data-today-actions]')?getJson(DATA.today):Promise.resolve({})), recommendationStatus(), getJson('public/data/recommendation-history.json').then(renderPerformance),
    ]);
    const recommendations = results[0].status === 'fulfilled' ? results[0].value : {};
    const today = results[1].status === 'fulfilled' ? results[1].value : {};

    renderMarket(results[2].status === 'fulfilled' ? results[2].value : null);
    renderRecommendations(results[2].status === 'fulfilled' ? results[2].value : null);
    renderToday(today, recommendations);
    setInterval(async()=>{
      if(document.hidden)return;
      try { const current=await recommendationStatus();renderMarket(current);renderRecommendations(current); }
      catch { renderMarket(null);renderRecommendations(null); }
    },60000);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
