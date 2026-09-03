(() => {
  'use strict';

  const exactText = new Map([
    ['DATA GATE', 'TRẠNG THÁI DỮ LIỆU'],
    ['BLOCKED_DATA_GATE', 'TẠM CHƯA PHÁT HÀNH'],
    ['INTERNAL REFERENCE', 'CHƯA XÁC NHẬN'],
    ['REFERENCE_ONLY', 'THAM CHIẾU'],
    ['TRA MÃ SẴN SÀNG', 'PHẠM VI THAM CHIẾU'],
    ['CHỜ NGUỒN ĐƯỢC CẤP QUYỀN', 'TẠM CHƯA PHÁT HÀNH'],
    ['CHỜ DỮ LIỆU ĐƯỢC CẤP QUYỀN', 'CHƯA ĐỦ DỮ LIỆU'],
    ['CHỜ DỮ LIỆU', 'CHƯA SẴN SÀNG'],
    ['CHƯA KẾT NỐI', 'CHƯA SẴN SÀNG'],
    ['Hồ sơ nội bộ', 'Phạm vi dữ liệu'],
    ['Hồ sơ tham chiếu nội bộ', 'Phạm vi dữ liệu'],
    ['Không cherry-pick.', 'Theo dõi đầy đủ từng khuyến nghị.'],
    ['NHẬT KÝ BẤT BIẾN', 'LỊCH SỬ THAY ĐỔI'],
    ['Chưa có recommendation được công bố cho mã này. Không tạo record để lấp chỗ trống.', 'Chưa có khuyến nghị công khai cho mã này.'],
    ['Không có recommendation thì không dựng nhật ký giả.', 'Chưa có thay đổi trạng thái được công bố.']
  ]);

  const marketLabels = {
    GREEN: 'XANH · THUẬN LỢI',
    YELLOW: 'VÀNG · THẬN TRỌNG',
    RED: 'ĐỎ · PHÒNG THỦ'
  };

  const publicState = {
    lookupLabel: 'ĐANG KIỂM TRA',
    lookupScope: 'ĐANG KIỂM TRA'
  };

  function siteUrl(path) {
    return new URL(String(path).replace(/^\/+/, ''), document.baseURI).toString();
  }

  function formatSnapshot(value) {
    if (!value) return '—';
    try {
      return new Intl.DateTimeFormat('vi-VN', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit', hour12: false
      }).format(new Date(value));
    } catch (_) {
      return '—';
    }
  }

  function replaceExactText(root = document.body) {
    if (!root || !document.createTreeWalker) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    let node;
    while ((node = walker.nextNode())) {
      const trimmed = String(node.nodeValue || '').trim();
      if (exactText.has(trimmed)) nodes.push([node, trimmed]);
    }
    nodes.forEach(([textNode, trimmed]) => {
      const replacement = exactText.get(trimmed);
      const raw = textNode.nodeValue;
      textNode.nodeValue = raw.replace(trimmed, replacement);
    });
  }

  function patchPortalShell() {
    const utility = document.querySelector('.portal-utility-inner');
    if (utility && utility.dataset.publicUx !== '1') {
      utility.dataset.publicUx = '1';
      utility.innerHTML = `
        <span><strong>STOCKRADAR.VN</strong><i></i>CỔ PHIẾU HOSE</span>
        <span class="portal-utility-note">Mốc quét: 10:30 · 11:15 · 13:30 · 14:15</span>`;
    }

    const tape = document.querySelector('.market-tape-inner');
    if (tape && tape.dataset.publicUx !== '1') {
      tape.dataset.publicUx = '1';
      tape.innerHTML = `
        <div class="tape-heading"><span class="live-dot" aria-hidden="true"></span><span>THỊ TRƯỜNG</span></div>
        <div class="tape-item"><span>Trạng thái</span><strong data-public-market>CHƯA SẴN SÀNG</strong></div>
        <div class="tape-item"><span>Giá/OHLCV</span><strong data-public-feed-status>CHƯA SẴN SÀNG</strong></div>
        <div class="tape-item tape-snapshot"><span>Cập nhật</span><strong data-public-snapshot>—</strong></div>
        <div class="tape-disclaimer">Chỉ phát hành tín hiệu khi dữ liệu đạt chuẩn</div>`;
    }

    const status = document.querySelector('.operations-status-grid');
    if (status && status.dataset.publicUx !== '1') {
      status.dataset.publicUx = '1';
      status.innerHTML = `
        <article><span>Thị trường</span><strong>HOSE</strong></article>
        <article><span>Dữ liệu giá</span><strong data-public-feed-status>CHƯA SẴN SÀNG</strong></article>
        <article><span>Tra cứu công khai</span><strong data-public-lookup-status>${publicState.lookupLabel}</strong></article>
        <article><span>Radar toàn HOSE</span><strong data-public-ranking-status>TẠM DỪNG</strong></article>`;
    }

    document.querySelectorAll('.site-footer .disclaimer').forEach(node => {
      const clean = 'StockRadar chỉ hiển thị tín hiệu khi dữ liệu thị trường đáp ứng điều kiện phát hành.';
      if (node.textContent !== clean) node.textContent = clean;
    });
  }

  function patchSearchScope() {
    if (document.body?.dataset.proposition !== 'ticker-search') return;

    const title = document.querySelector('.page-heading h1');
    if (title && title.textContent.trim() === 'Tra cứu cổ phiếu HOSE') title.textContent = 'Kiểm tra mã cổ phiếu';

    const headingPill = document.querySelector('.page-heading .data-pill');
    if (headingPill) headingPill.textContent = 'PHẠM VI THAM CHIẾU';

    document.querySelectorAll('.lookup-status-line > span').forEach(item => {
      const text = item.textContent.trim();
      const strong = item.querySelector('strong');
      if (!strong) return;
      if (text.startsWith('Tra mã:')) {
        strong.removeAttribute('data-reference-count');
        strong.dataset.publicLookupStatus = '';
        strong.textContent = publicState.lookupLabel;
      }
      if (text.startsWith('Nguồn:') || text.startsWith('Phạm vi công khai:')) {
        item.firstChild.nodeValue = 'Phạm vi công khai: ';
        strong.removeAttribute('data-reference-count');
        strong.dataset.publicLookupScope = '';
        strong.textContent = publicState.lookupScope;
      }
    });
  }

  function patchReadinessCards() {
    document.querySelectorAll('.data-readiness').forEach(card => {
      const label = card.querySelector('.panel-label');
      if (label && label.textContent !== 'TRẠNG THÁI DỮ LIỆU') label.textContent = 'TRẠNG THÁI DỮ LIỆU';
      const pill = card.querySelector('.data-pill');
      if (pill && pill.textContent !== 'TẠM CHƯA PHÁT HÀNH') pill.textContent = 'TẠM CHƯA PHÁT HÀNH';
      const grid = card.querySelector('.readiness-grid');
      if (grid && grid.dataset.publicUx !== '1') {
        grid.dataset.publicUx = '1';
        grid.innerHTML = `
          <div><span>Thị trường</span><strong>HOSE</strong></div>
          <div><span>Tra cứu công khai</span><strong data-public-lookup-status>${publicState.lookupLabel}</strong></div>
          <div><span>Dữ liệu giá</span><strong>CHƯA SẴN SÀNG</strong></div>
          <div><span>Radar toàn HOSE</span><strong>TẠM DỪNG</strong></div>`;
      }
    });
  }

  function patchTickerCards() {
    document.querySelectorAll('.ticker-accepted').forEach(card => {
      const label = card.querySelector('.panel-label');
      if (label) label.textContent = 'MÃ ĐÃ NHẬP';
      const pill = card.querySelector('.data-pill');
      if (pill) pill.textContent = 'CHƯA XÁC NHẬN NIÊM YẾT';
      const metrics = card.querySelector('.accepted-metrics');
      if (metrics && metrics.dataset.publicUx !== '1') {
        metrics.dataset.publicUx = '1';
        metrics.innerHTML = `
          <div><span>Định dạng mã</span><strong>HỢP LỆ</strong></div>
          <div><span>Niêm yết HOSE</span><strong>CHƯA XÁC NHẬN</strong></div>
          <div><span>Giá hiện tại</span><strong>—</strong></div>
          <div><span>Kết luận</span><strong>—</strong></div>`;
      }
    });

    document.querySelectorAll('.quick-lookup').forEach(card => {
      const label = card.querySelector('header .panel-label');
      if (label && /BLOCKED|INSUFFICIENT|TRẠNG THÁI/i.test(label.textContent)) label.textContent = 'BÁO CÁO CỔ PHIẾU';
      const pill = card.querySelector('header .data-pill');
      if (pill && /CHỜ|CẤP QUYỀN|TẠM/i.test(pill.textContent)) pill.textContent = 'CHƯA ĐỦ DỮ LIỆU';
    });
  }

  function applyLookupState() {
    document.querySelectorAll('[data-public-lookup-status]').forEach(node => { node.textContent = publicState.lookupLabel; });
    document.querySelectorAll('[data-public-lookup-scope]').forEach(node => { node.textContent = publicState.lookupScope; });
  }

  let refreshStarted = false;
  async function refreshPublicStatus() {
    if (refreshStarted) return;
    refreshStarted = true;
    try {
      const [masterResponse, radarResponse] = await Promise.all([
        fetch(siteUrl('public/data/ticker-universe.json'), { cache: 'no-store' }),
        fetch(siteUrl('public/data/radar.json'), { cache: 'no-store' })
      ]);
      const master = masterResponse.ok ? await masterResponse.json() : {};
      const radar = radarResponse.ok ? await radarResponse.json() : {};
      const reference = master.internal_reference || {};
      const masterStatus = String(master.data_status || master.status || '');
      const masterReady = Boolean(masterStatus && !masterStatus.startsWith('BLOCKED') && master.full_universe === true && master.data_grade === 'DECISION_GRADE');
      const publicItemCount = Array.isArray(master.items) ? master.items.length : 0;
      publicState.lookupLabel = masterReady ? 'TOÀN BỘ HOSE' : (publicItemCount ? `${publicItemCount} MÃ THAM CHIẾU` : 'CHƯA SẴN SÀNG');
      publicState.lookupScope = masterReady ? 'TOÀN BỘ HOSE' : (publicItemCount ? `${publicItemCount} MÃ` : 'CHƯA SẴN SÀNG');

      const radarStatus = String(radar.data_status || radar.status || '');
      const radarReady = Boolean(radarStatus && !radarStatus.startsWith('BLOCKED') && radar.snapshot?.data_grade === 'DECISION_GRADE');
      const feedReady = Boolean(reference.market_data_ready || radarReady);
      const rankingReady = Boolean(reference.ranking_ready || radarReady);
      const market = radarReady ? (marketLabels[radar.market_regime] || 'ĐANG THEO DÕI') : 'CHƯA SẴN SÀNG';
      const snapshot = reference.as_of || radar.snapshot?.as_of;

      applyLookupState();
      document.querySelectorAll('[data-public-market]').forEach(node => { node.textContent = market; });
      document.querySelectorAll('[data-public-feed-status]').forEach(node => { node.textContent = feedReady ? 'SẴN SÀNG' : 'CHƯA SẴN SÀNG'; });
      document.querySelectorAll('[data-public-ranking-status]').forEach(node => { node.textContent = rankingReady ? 'SẴN SÀNG' : 'TẠM DỪNG'; });
      document.querySelectorAll('[data-public-snapshot]').forEach(node => { node.textContent = formatSnapshot(snapshot); });
    } catch (_) {
      publicState.lookupLabel = 'CHƯA XÁC NHẬN';
      publicState.lookupScope = 'CHƯA XÁC NHẬN';
      applyLookupState();
      document.querySelectorAll('[data-public-market]').forEach(node => { node.textContent = 'CHƯA XÁC NHẬN'; });
      document.querySelectorAll('[data-public-feed-status]').forEach(node => { node.textContent = 'CHƯA XÁC NHẬN'; });
      document.querySelectorAll('[data-public-ranking-status]').forEach(node => { node.textContent = 'TẠM DỪNG'; });
    }
  }

  function applyPublicUx() {
    patchPortalShell();
    patchSearchScope();
    patchReadinessCards();
    patchTickerCards();
    replaceExactText();
    applyLookupState();
  }

  let scheduled = false;
  function scheduleApply() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      applyPublicUx();
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    applyPublicUx();
    refreshPublicStatus();
    const observer = new MutationObserver(scheduleApply);
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  });
})();