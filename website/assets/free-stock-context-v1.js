(() => {
  'use strict';

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

  function loadMarketReferenceAssets() {
    if (!document.querySelector('link[data-market-reference-style]')) {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.dataset.marketReferenceStyle = '';
      link.href = new URL('assets/public-market-reference-v1.css?v=20260904-market1', document.baseURI).toString();
      document.head.appendChild(link);
    }
    if (!document.querySelector('script[data-market-reference-script]')) {
      const script = document.createElement('script');
      script.src = new URL('assets/public-market-reference-v1.js?v=20260904-market2', document.baseURI).toString();
      script.async = true;
      script.dataset.marketReferenceScript = '';
      document.head.appendChild(script);
    }
  }

  let universePromise;
  function loadUniverse() {
    if (!universePromise) {
      universePromise = fetch(new URL('public/data/ticker-universe.json', document.baseURI), { cache: 'no-store' })
        .then(response => response.ok ? response.json() : { items: [] })
        .catch(() => ({ items: [] }));
    }
    return universePromise;
  }

  function fullPublicReportPresent(target) {
    return Boolean(target.querySelector('.position-detail-grid, .ticker-history, .evidence-grid'));
  }

  function clearFallback(target) {
    target.querySelector('[data-free-stock-context]')?.remove();
    target.classList.remove('has-free-context');
  }

  function markup(ticker, security) {
    const verified = Boolean(security);
    const company = verified
      ? security.company_name || 'Doanh nghiệp đã được xác minh trong universe công khai'
      : 'Mã đã được nhận; dữ liệu giá/biểu đồ tham chiếu hiển thị trực tiếp phía dưới';
    const sector = verified
      ? security.sector || 'Chưa có phân loại ngành trong feed công khai'
      : 'Kết luận riêng của StockRadar vẫn chờ feed production được cấp quyền';
    const releaseState = verified ? 'ĐÃ XÁC MINH CÔNG KHAI' : 'DECISION FEED ĐANG CHỜ';
    return `
      <section class="free-context-card" data-free-stock-context>
        <header class="free-context-head">
          <div><span class="panel-label">FREE · BỐI CẢNH STOCKRADAR</span><h3>${escapeHtml(ticker)}</h3><p>${escapeHtml(company)} · ${escapeHtml(sector)}</p></div>
          <span class="free-context-status ${verified ? 'is-verified' : ''}">${releaseState}</span>
        </header>
        <div class="free-context-horizons" aria-label="Bốn khung đầu tư">
          <div><span>5–20 phiên</span><strong>Ngắn hạn</strong><small>Xem giá/biểu đồ tham chiếu bên dưới; quyết định StockRadar chưa phát hành.</small></div>
          <div><span>1–6 tháng</span><strong>Trung hạn</strong><small>Xem giá/biểu đồ tham chiếu bên dưới; quyết định StockRadar chưa phát hành.</small></div>
          <div><span>6–18 tháng</span><strong>Dài hạn</strong><small>Xem hồ sơ/tài chính tham chiếu bên dưới; Fair Value StockRadar chưa phát hành.</small></div>
          <div><span>2–5 năm+</span><strong>Tích sản</strong><small>Xem hồ sơ/tài chính tham chiếu bên dưới; luận điểm StockRadar chưa phát hành.</small></div>
        </div>
        <div class="free-context-grid">
          <article><strong>Free có ngay</strong><ul><li>Giá và biểu đồ mã HOSE qua widget hiển thị trực tiếp.</li><li>Hồ sơ doanh nghiệp và dữ liệu tài chính tham chiếu khi TradingView hỗ trợ mã.</li><li>Bốn khung đầu tư và lịch sử khuyến nghị StockRadar khi feed được phát hành.</li></ul></article>
          <article><strong>StockRadar không tự dựng</strong><ul><li>Không bịa Fair Value, Buy Zone, Stop hay Target khi feed production chưa đạt gate.</li><li>Không dùng tín hiệu/điểm của bên hiển thị tham chiếu làm tín hiệu StockRadar.</li><li>Không biến dữ liệu nghiên cứu nội bộ thành dữ liệu khách hàng khi chưa có quyền phát hành.</li></ul></article>
        </div>
        <div class="free-context-conclusion"><span>Trạng thái quyết định StockRadar</span><strong>CHƯA PHÁT HÀNH MUA/BÁN — DỮ LIỆU THỊ TRƯỜNG THAM CHIẾU VẪN XEM ĐƯỢC BÊN DƯỚI</strong><p>Khi production manifest hợp lệ và Decision Gate đạt chuẩn, phần này tự thay bằng điểm, xếp hạng, trạng thái 4 khung và kết luận thực tế của StockRadar.</p></div>
      </section>`;
  }

  async function enhance(target) {
    if (!target) return;
    if (fullPublicReportPresent(target)) {
      clearFallback(target);
      return;
    }
    if (target.querySelector('[data-free-stock-context]')) return;
    if (!target.querySelector('.data-readiness, .ticker-accepted, .lookup-quick-result')) return;
    const ticker = tickerFromLocation();
    if (!ticker) return;
    const payload = await loadUniverse();
    if (fullPublicReportPresent(target)) {
      clearFallback(target);
      return;
    }
    if (target.querySelector('[data-free-stock-context]')) return;
    const security = Array.isArray(payload.items) ? payload.items.find(item => item.ticker === ticker) : null;
    target.insertAdjacentHTML('afterbegin', markup(ticker, security));
    target.classList.add('has-free-context');
  }

  function mount() {
    loadMarketReferenceAssets();
    const target = document.querySelector('[data-dynamic-stock-report]');
    if (!target) return;
    const run = () => enhance(target);
    run();
    new MutationObserver(run).observe(target, { childList: true, subtree: true });
  }

  document.addEventListener('DOMContentLoaded', mount, { once: true });
})();
