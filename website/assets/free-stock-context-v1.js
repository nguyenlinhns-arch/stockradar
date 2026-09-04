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
      : 'StockRadar đã nhận mã; feed phát hành công khai hiện chưa có manifest xác minh cho mã này';
    const sector = verified
      ? security.sector || 'Chưa có phân loại ngành trong feed công khai'
      : 'Không tự suy luận doanh nghiệp/ngành khi publication gate chưa mở';
    const releaseState = verified ? 'ĐÃ XÁC MINH CÔNG KHAI' : 'CHỜ GATE PHÁT HÀNH';
    return `
      <section class="free-context-card" data-free-stock-context>
        <header class="free-context-head">
          <div><span class="panel-label">BẢN FREE · BỐI CẢNH CÓ THỂ PHÁT HÀNH</span><h3>${escapeHtml(ticker)}</h3><p>${escapeHtml(company)} · ${escapeHtml(sector)}</p></div>
          <span class="free-context-status ${verified ? 'is-verified' : ''}">${releaseState}</span>
        </header>
        <div class="free-context-horizons" aria-label="Bốn khung đầu tư">
          <div><span>5–20 phiên</span><strong>Ngắn hạn</strong><small>Chưa phát hành kết luận hành động ở feed công khai hiện tại.</small></div>
          <div><span>1–6 tháng</span><strong>Trung hạn</strong><small>Chưa phát hành kết luận hành động ở feed công khai hiện tại.</small></div>
          <div><span>6–18 tháng</span><strong>Dài hạn</strong><small>Chưa phát hành kết luận hành động ở feed công khai hiện tại.</small></div>
          <div><span>2–5 năm+</span><strong>Tích sản</strong><small>Chưa phát hành kết luận hành động ở feed công khai hiện tại.</small></div>
        </div>
        <div class="free-context-grid">
          <article><strong>Free hiển thị</strong><ul><li>Thông tin doanh nghiệp/ngành khi đã qua publication gate.</li><li>Bốn khung đầu tư tách biệt và trạng thái Radar theo snapshot.</li><li>Lịch sử khuyến nghị đã được phát hành công khai.</li></ul></article>
          <article><strong>Free không tự dựng</strong><ul><li>Không bịa giá, Fair Value, Buy Zone, Stop hay Target khi feed được cấp quyền chưa sẵn sàng.</li><li>Không biến thứ hạng Radar thành khuyến nghị mua.</li><li>Không coi dữ liệu nội bộ là dữ liệu được phép phát hành chỉ vì scanner đã tính xong.</li></ul></article>
        </div>
        <div class="free-context-conclusion"><span>Trạng thái phát hành hiện tại</span><strong>CHƯA PHÁT HÀNH TÍN HIỆU MUA/BÁN CHO SNAPSHOT CÔNG KHAI NÀY</strong><p>Radar nội bộ và feed công khai là hai gate độc lập. Khi manifest dữ liệu hợp lệ và Decision Gate đạt chuẩn, trang sẽ tự động thay phần này bằng kết luận thực tế.</p></div>
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
    const target = document.querySelector('[data-dynamic-stock-report]');
    if (!target) return;
    const run = () => enhance(target);
    run();
    new MutationObserver(run).observe(target, { childList: true, subtree: true });
  }

  document.addEventListener('DOMContentLoaded', mount, { once: true });
})();
