(() => {
  'use strict';

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
    }[character]));
  }

  function tickerFromLocation() {
    const pathParts = location.pathname.split('/').filter(Boolean);
    const routeTicker = pathParts[pathParts.length - 1] !== 'co-phieu' ? pathParts[pathParts.length - 1] : '';
    const raw = new URLSearchParams(location.search).get('ticker') || routeTicker;
    const ticker = String(raw || '').trim().toUpperCase();
    return /^[A-Z]{3}$/.test(ticker) ? ticker : '';
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

  function markup(ticker, security) {
    const company = security?.company_name || 'Chưa có tên doanh nghiệp trong lớp dữ liệu công khai';
    const sector = security?.sector || 'Chưa xác minh ngành trong lớp dữ liệu công khai';
    const verified = Boolean(security);
    return `
      <section class="free-context-card" data-free-stock-context>
        <header class="free-context-head">
          <div><span class="panel-label">BẢN FREE · THÔNG TIN CÓ THỂ KẾT LUẬN</span><h3>${escapeHtml(ticker)}</h3><p>${escapeHtml(company)} · ${escapeHtml(sector)}</p></div>
          <span class="free-context-status ${verified ? 'is-verified' : ''}">${verified ? 'ĐÃ ĐỐI CHIẾU' : 'CHỜ ĐỐI CHIẾU'}</span>
        </header>
        <div class="free-context-horizons" aria-label="Bốn khung đầu tư">
          <div><span>5–20 phiên</span><strong>Ngắn hạn</strong><small>Chưa đủ dữ liệu định lượng để phát hành hành động.</small></div>
          <div><span>1–6 tháng</span><strong>Trung hạn</strong><small>Chưa đủ dữ liệu định lượng để phát hành hành động.</small></div>
          <div><span>6–18 tháng</span><strong>Dài hạn</strong><small>Chưa đủ dữ liệu định lượng để phát hành hành động.</small></div>
          <div><span>2–5 năm+</span><strong>Tích sản</strong><small>Chưa đủ dữ liệu định lượng để phát hành hành động.</small></div>
        </div>
        <div class="free-context-grid">
          <article><strong>Free đang có</strong><ul><li>Mã và thông tin doanh nghiệp/ngành khi đã đối chiếu công khai.</li><li>Bốn góc nhìn đầu tư tách biệt.</li><li>Trạng thái và lịch sử khuyến nghị công khai nếu đã phát hành.</li></ul></article>
          <article><strong>Free chưa suy luận</strong><ul><li>Không dựng giá, định giá, Buy Zone, Stop hay Target khi nguồn chưa đạt chuẩn.</li><li>Không biến danh sách Radar thành khuyến nghị mua.</li><li>Không biến trạng thái thiếu dữ liệu thành nhận định tích cực hoặc tiêu cực.</li></ul></article>
        </div>
        <div class="free-context-conclusion"><span>Kết luận hiện tại</span><strong>CHƯA CÓ CƠ SỞ DỮ LIỆU ĐỦ ĐỂ ĐƯA RA HÀNH ĐỘNG MUA/BÁN</strong><p>Đây là kết luận có chủ đích của bản Free khi dữ liệu chưa đáp ứng điều kiện phát hành, không phải lỗi tra cứu.</p></div>
      </section>`;
  }

  async function enhance(target) {
    if (!target || target.querySelector('[data-free-stock-context]')) return;
    if (target.querySelector('.position-detail-grid, .ticker-history, .evidence-grid')) return;
    if (!target.querySelector('.data-readiness, .ticker-accepted, .lookup-quick-result')) return;
    const ticker = tickerFromLocation();
    if (!ticker) return;
    const payload = await loadUniverse();
    if (target.querySelector('[data-free-stock-context]')) return;
    if (target.querySelector('.position-detail-grid, .ticker-history, .evidence-grid')) return;
    const security = Array.isArray(payload.items) ? payload.items.find(item => item.ticker === ticker) : null;
    target.insertAdjacentHTML('afterbegin', markup(ticker, security));
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