(() => {
  'use strict';

  const TOP_DATA = 'public/data/top-stocks.json';
  const UNIVERSE_DATA = 'public/data/ticker-universe.json';
  const RECOMMENDATION_DATA = 'public/data/recommendations.json';

  const config = () => window.STOCKRADAR_BUYER_CONFIG || window.STOCKRADAR_AUTH_CONFIG || {};
  const emailReady = () => config().emailDeliveryReady === true;
  const checkoutReady = () => config().checkoutReady === true;

  const url = path => new URL(path, document.baseURI).href;
  const stockUrl = ticker => url(`co-phieu/${encodeURIComponent(ticker)}/`);

  async function json(path) {
    const response = await fetch(url(path), { cache: 'no-store', credentials: 'omit' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[char]);
  }

  function currentTicker() {
    const staticTicker = String(document.body?.dataset?.staticTicker || '').trim().toUpperCase();
    if (/^(?=.*[A-Z])[A-Z0-9]{3}$/.test(staticTicker)) return staticTicker;
    const query = new URLSearchParams(location.search).get('ticker');
    const ticker = String(query || '').trim().toUpperCase();
    return /^(?=.*[A-Z])[A-Z0-9]{3}$/.test(ticker) ? ticker : '';
  }

  function rewriteConversionLinks() {
    if (!checkoutReady()) {
      document.querySelectorAll('a[href*="thanh-toan/"]').forEach(link => {
        link.href = url('dang-ky/#premium-notify-title');
        if (/thanh toán|nâng premium|premium\s*·?\s*199/i.test(link.textContent || '')) {
          link.textContent = 'Đăng ký quan tâm Premium';
        }
      });
    }

    if (!emailReady()) {
      document.querySelectorAll('.header-register-cta').forEach(link => {
        link.href = url('dang-ky/');
        link.textContent = 'Đăng ký';
        link.setAttribute('aria-label', 'Xem gói Free và Premium của StockRadar');
      });

      const lead = document.querySelector('.home-lead-card');
      if (lead) {
        lead.classList.add('buyer-start-card');
        lead.innerHTML = `
          <span>FREE + PREMIUM</span>
          <strong>Bắt đầu với StockRadar</strong>
          <p>Tra cứu cổ phiếu, xem Radar rà soát và chọn gói phù hợp với nhu cầu phân tích.</p>
          <div class="buyer-start-actions">
            <a class="button button-primary" href="${url('kiem-tra-co-phieu/')}">Tra cứu cổ phiếu</a>
            <a class="button button-secondary" href="${url('dang-ky/')}">Xem Free & Premium</a>
          </div>`;
      }

      document.querySelectorAll('[data-conversion-free-lead], [data-conversion-mobile-lead]').forEach(link => {
        link.href = url('dang-ky/');
        link.textContent = 'Đăng ký';
      });

      document.querySelectorAll('.conversion-rail-copy').forEach(block => {
        const strong = block.querySelector('strong');
        const p = block.querySelector('p');
        if (strong) strong.textContent = 'Dùng StockRadar Free để tra cứu và theo dõi. Nâng Premium khi cần kế hoạch hành động.';
        if (p) p.textContent = 'Premium mở rộng phân tích doanh nghiệp, định giá, Buy Zone, Stop, Target, Risk/Reward và cảnh báo hành động theo quyền gói.';
      });
    }

    const valueStrip = document.querySelector('.home-value-strip');
    if (valueStrip) {
      const cells = valueStrip.querySelectorAll(':scope > div');
      if (cells[0]) cells[0].innerHTML = '<strong>Top HOSE · StockRadar</strong><span>Top mạnh nhất và Top theo ngành theo điểm StockRadar khi snapshot đạt chuẩn.</span>';
      if (cells[1]) cells[1].innerHTML = '<strong>Decision Card</strong><span>Score · xếp hạng · định giá · Buy Zone · Stop · Target · Risk/Reward khi có dữ liệu hợp lệ.</span>';
      if (cells[2]) cells[2].innerHTML = '<strong>Free → Premium</strong><span>Trải nghiệm công cụ trước; chỉ nâng cấp khi cần chiều sâu phân tích và cảnh báo.</span>';
    }
  }

  function rankingPolicy() {
    return `
      <div class="buyer-top-policy">
        <strong>Xếp hạng StockRadar</strong>
        <span>Chỉ cổ phiếu vượt đủ dữ liệu, thanh khoản, 4M/CANSLIM, SEPA/VCP, VPA, định giá và Risk/Reward mới xuất hiện trong bảng Top.</span>
      </div>`;
  }

  function strongestRows(items) {
    return `
      <div class="buyer-top-table">
        <div class="buyer-top-row buyer-top-head"><span>#</span><span>Mã</span><span>Ngành</span><span>Điểm</span><span>Trạng thái</span></div>
        ${items.map(item => `
          <a class="buyer-top-row" href="${stockUrl(item.ticker)}">
            <b>${esc(item.rank)}</b><strong>${esc(item.ticker)}</strong><span>${esc(item.sector)}</span><em>${esc(item.score)}/100</em><small>${esc(item.state)}</small>
          </a>`).join('')}
      </div>`;
  }

  function sectorRows(groups) {
    return `<div class="buyer-sector-top">${groups.map(group => `
      <section><header><strong>${esc(group.sector)}</strong></header>
        <div>${(group.items || []).map(item => `<a href="${stockUrl(item.ticker)}"><b>#${esc(item.sector_rank)}</b><strong>${esc(item.ticker)}</strong><span>${esc(item.score)}/100</span></a>`).join('')}</div>
      </section>`).join('')}</div>`;
  }

  function createTopModule(payload) {
    const section = document.createElement('section');
    section.className = 'buyer-top-hose';
    section.dataset.topHose = '';
    section.innerHTML = `
      <header class="buyer-top-title">
        <div><span>TOP CỔ PHIẾU HOSE</span><h3>Top cổ phiếu HOSE theo tiêu chí StockRadar.vn</h3></div>
        <small>4M · CANSLIM · SEPA/VCP · VPA · định giá · thanh khoản · R:R</small>
      </header>
      <div class="buyer-top-tabs" role="tablist">
        <button type="button" class="is-active" data-top-tab="strongest">Top mạnh nhất</button>
        <button type="button" data-top-tab="sector">Top theo ngành</button>
      </div>
      <div class="buyer-top-content" data-top-content></div>`;

    const content = section.querySelector('[data-top-content]');
    const valid = payload?.ranking_valid === true && Array.isArray(payload.strongest) && payload.strongest.length;
    const render = mode => {
      section.querySelectorAll('[data-top-tab]').forEach(button => button.classList.toggle('is-active', button.dataset.topTab === mode));
      if (!valid) {
        content.innerHTML = rankingPolicy();
        return;
      }
      content.innerHTML = mode === 'sector' ? sectorRows(payload.by_sector || []) : strongestRows(payload.strongest || []);
    };
    section.querySelectorAll('[data-top-tab]').forEach(button => button.addEventListener('click', () => render(button.dataset.topTab)));
    render('strongest');
    return section;
  }

  async function mountTopHose() {
    const homeList = document.querySelector('.home-radar-sector-list');
    const radarWorkspace = document.querySelector('.radar-workspace .workspace-panel');
    if (!homeList && !radarWorkspace) return;

    let payload = { ranking_valid: false, strongest: [], by_sector: [] };
    try { payload = await json(TOP_DATA); } catch (_) {}
    const module = createTopModule(payload);

    if (homeList) {
      const homePanel = homeList.closest('.home-focus-panel');
      const heading = homePanel?.querySelector('.home-focus-head h2');
      const description = homePanel?.querySelector('.home-focus-head p');
      if (heading) heading.textContent = 'Danh sách cổ phiếu theo Radar rà soát';
      if (description) description.textContent = '30 mã HOSE cân bằng 10 nhóm ngành để Radar theo dõi và rà soát.';
      homeList.parentNode.insertBefore(module, homeList);
      const note = homePanel?.querySelector('.home-radar-note');
      if (note) note.textContent = 'Radar 30 là phạm vi rà soát cân bằng ngành; không mặc định đồng nghĩa Top mạnh nhất hoặc khuyến nghị mua.';
    } else if (radarWorkspace) {
      radarWorkspace.insertBefore(module, radarWorkspace.firstChild);
    }
  }

  function metric(label, value, suffix = '') {
    if (value === null || value === undefined || value === '') return '';
    return `<div class="decision-metric"><span>${esc(label)}</span><strong>${esc(value)}${esc(suffix)}</strong></div>`;
  }

  function formatBuyZone(rec) {
    if (rec?.recommended_buy_low == null || rec?.recommended_buy_high == null) return null;
    return `${rec.recommended_buy_low}–${rec.recommended_buy_high}`;
  }

  async function mountDecisionCard() {
    if (document.body?.dataset?.proposition !== 'stock-report') return;
    const ticker = currentTicker();
    if (!ticker) return;
    const target = document.querySelector('.analysis-tier-grid');
    if (!target || document.querySelector('[data-decision-card]')) return;

    let universe = { items: [] }, top = { ranking_valid: false }, recs = { items: [] };
    try { [universe, top, recs] = await Promise.all([json(UNIVERSE_DATA), json(TOP_DATA), json(RECOMMENDATION_DATA)]); } catch (_) {}

    const identity = (universe.items || []).find(item => item.ticker === ticker) || {};
    const ranked = top.ranking_valid === true ? (top.strongest || []).find(item => item.ticker === ticker) : null;
    const recommendation = (recs.items || []).find(item => item.ticker === ticker && String(item.publish_status || '').toUpperCase() === 'PUBLISHED') || null;

    const card = document.createElement('section');
    card.className = 'stock-decision-card';
    card.dataset.decisionCard = '';
    const metrics = [
      metric('StockRadar Score', ranked?.score, ranked?.score != null ? '/100' : ''),
      metric('Xếp hạng HOSE', ranked?.rank ? `#${ranked.rank}` : null),
      metric('Xếp hạng ngành', ranked?.sector_rank ? `#${ranked.sector_rank}` : null),
      metric('Buy Zone', formatBuyZone(recommendation)),
      metric('Stop', recommendation?.stop_loss),
      metric('Target', recommendation?.target_price),
      metric('Risk/Reward', recommendation?.risk_reward),
    ].filter(Boolean).join('');

    card.innerHTML = `
      <div class="decision-identity">
        <span>DECISION CARD</span>
        <h1>${esc(ticker)}</h1>
        <p>${esc(identity.company_name || '')}${identity.sector ? ` · ${esc(identity.sector)}` : ''}</p>
      </div>
      <div class="decision-thesis">
        <span>Góc nhìn StockRadar</span>
        <strong>${recommendation ? esc(recommendation.recommendation_state || recommendation.status || 'PHÂN TÍCH') : 'PHÂN TÍCH ĐA KHUNG'}</strong>
        <p>4M · CANSLIM · định giá · SEPA/VCP · VPA · quản trị rủi ro.</p>
      </div>
      ${metrics ? `<div class="decision-metrics">${metrics}</div>` : ''}`;
    target.parentNode.insertBefore(card, target);
  }

  async function mount() {
    rewriteConversionLinks();
    await Promise.allSettled([mountTopHose(), mountDecisionCard()]);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
