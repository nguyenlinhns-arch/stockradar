(() => {
  const proposition = document.body?.dataset?.proposition || '';
  const fallbackRoutes = new Set([
    'radar5', 'breakout', 'risk', 'track-record', 'today-changes',
    'performance', 'sector', 'ticker-search', 'stock-search', 'stock-report'
  ]);

  const copyReplacements = new Map([
    ['DATA GATE', 'TRẠNG THÁI DỮ LIỆU'],
    ['GATE', 'TRẠNG THÁI'],
    ['BLOCKED_DATA_GATE', 'CHƯA ĐỦ DỮ LIỆU'],
    ['CHỜ NGUỒN ĐƯỢC CẤP QUYỀN', 'CHƯA ĐỦ NGUỒN GIÁ'],
    ['CHỜ DỮ LIỆU ĐƯỢC CẤP QUYỀN', 'CHƯA ĐỦ DỮ LIỆU'],
    ['ĐANG KHÓA', 'CHƯA PHÁT HÀNH'],
    ['Hồ sơ tham chiếu nội bộ', 'Hồ sơ HOSE tham chiếu'],
    ['Hồ sơ nội bộ', 'Hồ sơ HOSE'],
    ['Giá/OHLCV đang chờ nguồn được cấp quyền', 'Giá/OHLCV chưa được phát hành'],
    ['Giá/OHLCV chưa kết nối', 'Giá/OHLCV chưa được phát hành'],
    ['Dữ liệu đã vượt Data Gate', 'Dữ liệu đã đạt điều kiện phát hành'],
    ['Record đang hiệu lực', 'Khuyến nghị đang hiệu lực'],
    ['Snapshot đã công bố', 'Lịch sử đã công bố'],
    ['Data grade', 'Cấp dữ liệu'],
    ['Kết quả chỉ được phát hành khi dữ liệu thị trường và quyền sử dụng đã vượt qua Data Gate.', 'Kết quả chỉ được phát hành khi dữ liệu thị trường và quyền sử dụng tương ứng đã đạt điều kiện.']
  ]);

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"]/g, character => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'
    }[character]));
  }

  function siteUrl(path) {
    return new URL(String(path).replace(/^\/+/, ''), document.baseURI).toString();
  }

  async function loadJson(path) {
    const response = await fetch(siteUrl(path), { cache: 'no-cache' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  function isBlocked(payload) {
    const status = String(payload?.data_status || payload?.status || '').toUpperCase();
    return !payload || !status || status.startsWith('BLOCKED');
  }

  function registerButton(label = 'Đăng ký bản tin') {
    return `<a class="button button-primary" href="dang-ky/">${label}</a>`;
  }

  function tickerLink(ticker) {
    return `co-phieu/?ticker=${encodeURIComponent(ticker)}`;
  }

  function referenceGrid(items) {
    return `<div class="v4-reference-grid">${items.map(item => `
      <a class="v4-reference-item" href="${tickerLink(item.ticker)}">
        <b>${escapeHtml(item.ticker)}</b>
        <span>${escapeHtml(item.sector || 'HOSE')}</span>
        <em>THEO DÕI</em>
      </a>`).join('')}</div>`;
  }

  function sectorGrid(items) {
    const groups = new Map();
    items.forEach(item => {
      const sector = item.sector || 'Khác';
      if (!groups.has(sector)) groups.set(sector, []);
      groups.get(sector).push(item);
    });
    const sorted = [...groups.entries()].sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0], 'vi'));
    return `<div class="v4-sector-grid">${sorted.map(([sector, stocks]) => `
      <article class="v4-sector-card">
        <strong>${escapeHtml(sector)}</strong>
        <small>${stocks.length} mã tham chiếu</small>
        <div class="v4-sector-tickers">${stocks.map(item => `<a href="${tickerLink(item.ticker)}">${escapeHtml(item.ticker)}</a>`).join('')}</div>
      </article>`).join('')}</div>`;
  }

  function zeroBar(cells) {
    return `<div class="v4-zero-bar">${cells.map(cell => `<div><span>${escapeHtml(cell.label)}</span><strong>${escapeHtml(cell.value)}</strong>${cell.note ? `<small>${escapeHtml(cell.note)}</small>` : ''}</div>`).join('')}</div>`;
  }

  function fallbackSection({ key, title, description, body, note, cta = true }) {
    return `<section class="v4-fallback" data-v4-fallback="${escapeHtml(key)}">
      <header class="v4-fallback-head">
        <div><span class="panel-label">DỮ LIỆU THAM CHIẾU</span><h2>${escapeHtml(title)}</h2><p>${escapeHtml(description)}</p></div>
        ${cta ? registerButton() : ''}
      </header>
      ${body}
      ${note ? `<div class="v4-fallback-note">${escapeHtml(note)}</div>` : ''}
    </section>`;
  }

  function insertAfter(target, html, key) {
    if (!target || document.querySelector(`[data-v4-fallback="${key}"]`)) return;
    target.insertAdjacentHTML('afterend', html);
  }

  function publishedCount(payload) {
    return Array.isArray(payload?.items) ? payload.items.length : 0;
  }

  function performanceCells(payload) {
    const summary = payload?.performance_summary || {};
    return [
      { label: 'Khuyến nghị đã phát hành', value: String(summary.total_published ?? publishedCount(payload)), note: 'Chỉ record công khai' },
      { label: 'Đang mở', value: String(summary.open ?? 0), note: 'Chưa khóa kết quả' },
      { label: 'Đã đóng', value: String(summary.closed ?? 0), note: 'Kết quả đã khóa' },
      { label: 'Tỷ lệ thắng', value: summary.win_rate_pct == null ? 'Chưa đủ mẫu' : `${summary.win_rate_pct}%`, note: 'Chỉ tính record đã đóng' }
    ];
  }

  function methodGrid(type) {
    if (type === 'performance') {
      return `<div class="v4-method-grid">
        <article><strong>Không tính mã chưa kích hoạt</strong><span>Khuyến nghị chưa chạm vùng mua không được đưa vào lãi/lỗ.</span></article>
        <article><strong>Entry có quy tắc</strong><span>Hiệu quả chỉ bắt đầu từ lần chạm hợp lệ đầu tiên sau thời điểm công bố.</span></article>
        <article><strong>Kết quả đóng mới là kết quả khóa</strong><span>Record đang mở chỉ là mark-to-market và có thể thay đổi.</span></article>
      </div>`;
    }
    return `<div class="v4-method-grid">
      <article><strong>Mỗi lần công bố có dấu thời gian</strong><span>Không sửa lịch sử để làm đẹp kết quả.</span></article>
      <article><strong>Trạng thái có vòng đời</strong><span>Chưa kích hoạt, đang hiệu lực và đã đóng được tách riêng.</span></article>
      <article><strong>Không có dữ liệu thì không tạo record</strong><span>StockRadar giữ trạng thái trống thay vì điền số liệu giả.</span></article>
    </div>`;
  }

  function routePayloadPath() {
    if (proposition === 'radar5' || proposition === 'breakout') return 'public/data/radar.json';
    if (proposition === 'risk' || proposition === 'today-changes') return 'public/data/today-changes.json';
    if (proposition === 'performance') return 'public/data/recommendations.json';
    if (proposition === 'track-record') return 'public/data/track-record.json';
    return null;
  }

  function enhanceRoute(master, payload) {
    const items = Array.isArray(master?.items) ? master.items.filter(item => item.active !== false) : [];
    if (!items.length) return;

    if (proposition === 'radar5') {
      const target = document.querySelector('[data-radar-table]');
      const body = zeroBar([
        { label: 'Xếp hạng đã phát hành', value: String(isBlocked(payload) ? 0 : publishedCount(payload)), note: 'Snapshot hiện tại' },
        { label: 'Mã tham chiếu', value: String(items.length), note: 'Danh sách công khai' },
        { label: 'Phạm vi', value: 'HOSE', note: 'Không HNX/UPCoM' },
        { label: 'Trạng thái', value: isBlocked(payload) ? 'THEO DÕI' : 'ĐÃ PHÁT HÀNH', note: 'Không tạo thứ hạng giả' }
      ]) + referenceGrid(items);
      insertAfter(target, fallbackSection({ key: 'radar-reference', title: `${items.length} mã HOSE đang theo dõi`, description: 'Radar chưa phát hành thứ hạng khi feed giá chưa đạt điều kiện; danh sách tham chiếu vẫn được hiển thị cụ thể.', body, note: 'THEO DÕI không đồng nghĩa khuyến nghị mua. Khi đủ dữ liệu, bảng Radar phía trên mới hiển thị điểm, setup, giá và khoảng cách tới pivot.' }), 'radar-reference');
      return;
    }

    if (proposition === 'breakout') {
      const target = document.querySelector('[data-radar-table]');
      const body = zeroBar([
        { label: 'Điểm mua đã phát hành', value: String(isBlocked(payload) ? 0 : publishedCount(payload)), note: 'Snapshot hiện tại' },
        { label: 'Mã tham chiếu', value: String(items.length), note: 'Đang theo dõi' },
        { label: 'Setup', value: 'Pocket / Breakout', note: 'Chỉ hiện khi đủ điều kiện' },
        { label: 'Hành động', value: 'CHỜ', note: 'Không mua đuổi' }
      ]) + referenceGrid(items);
      insertAfter(target, fallbackSection({ key: 'breakout-reference', title: 'Danh sách theo dõi trước điểm mua', description: 'Không có tín hiệu được phát hành thì StockRadar giữ nguyên trạng thái theo dõi thay vì tạo điểm mua giả.', body, note: 'Buy Zone, Stop-loss, Target và R:R chỉ xuất hiện sau khi một setup vượt đủ điều kiện phát hành.' }), 'breakout-reference');
      return;
    }

    if (proposition === 'risk') {
      const target = document.querySelector('[data-risk-alerts]');
      const body = zeroBar([
        { label: 'Cảnh báo hành động', value: String(isBlocked(payload) ? 0 : publishedCount(payload)), note: 'Snapshot hiện tại' },
        { label: 'Mã tham chiếu', value: String(items.length), note: 'Đang theo dõi' },
        { label: 'Phạm vi', value: 'HOSE', note: 'Cổ phiếu công khai' },
        { label: 'Nguyên tắc', value: 'CHỈ BÁO KHI CẦN', note: 'Không spam cảnh báo' }
      ]) + referenceGrid(items);
      insertAfter(target, fallbackSection({ key: 'risk-reference', title: 'Mã đang nằm trong phạm vi theo dõi rủi ro', description: 'Chưa có cảnh báo hành động được phát hành ở snapshot công khai hiện tại.', body, note: 'Cảnh báo hạ tỷ trọng/cắt lỗ chỉ được phát hành khi có record hợp lệ và điều kiện rủi ro thực sự bị kích hoạt.' }), 'risk-reference');
      return;
    }

    if (proposition === 'today-changes') {
      const target = document.querySelector('[data-today-changes]');
      const body = zeroBar([
        { label: 'Thay đổi đã phát hành', value: String(isBlocked(payload) ? 0 : publishedCount(payload)), note: 'Snapshot hiện tại' },
        { label: 'Mã tham chiếu', value: String(items.length), note: 'Đang theo dõi' },
        { label: 'Nhiễu thấp', value: 'ƯU TIÊN', note: 'Chỉ thay đổi đáng kể' },
        { label: 'Phạm vi', value: 'HOSE', note: 'Danh mục công khai' }
      ]) + referenceGrid(items);
      insertAfter(target, fallbackSection({ key: 'today-reference', title: 'Danh sách đang được kiểm tra thay đổi', description: 'Không có thay đổi đủ tiêu chuẩn thì trang vẫn cho biết rõ phạm vi mã đang theo dõi.', body, note: 'Trang này không biến dao động nhỏ thành tín hiệu hành động.' }), 'today-reference');
      return;
    }

    if (proposition === 'performance') {
      const target = document.querySelector('[data-performance-summary]');
      const body = zeroBar(performanceCells(payload)) + methodGrid('performance');
      insertAfter(target, fallbackSection({ key: 'performance-method', title: 'Cách StockRadar đo hiệu quả', description: 'Khi chưa có khuyến nghị đã đóng, tỷ lệ thắng và lợi nhuận trung bình được để trống thay vì ước đoán.', body, note: 'Past performance không đảm bảo kết quả tương lai; số liệu chỉ có ý nghĩa khi đủ mẫu và cùng phương pháp tính.' }), 'performance-method');
      return;
    }

    if (proposition === 'track-record') {
      const target = document.querySelector('[data-track-record]');
      const body = zeroBar([
        { label: 'Record công khai', value: String(isBlocked(payload) ? 0 : publishedCount(payload)), note: 'Lịch sử hiện tại' },
        { label: 'Phạm vi', value: 'HOSE', note: 'Theo chuẩn StockRadar' },
        { label: 'Sửa lịch sử', value: 'KHÔNG', note: 'Append-only' },
        { label: 'Trạng thái', value: isBlocked(payload) ? 'CHƯA CÓ RECORD' : 'ĐÃ CÓ DỮ LIỆU', note: 'Không dựng lịch sử giả' }
      ]) + methodGrid('track');
      insertAfter(target, fallbackSection({ key: 'track-method', title: 'Nguyên tắc lưu lịch sử công bố', description: 'Lịch sử chỉ bắt đầu khi có snapshot khuyến nghị thật được phát hành.', body, note: 'Mỗi record giữ dấu thời gian, trạng thái kích hoạt và kết quả theo cùng một quy tắc đo.' }), 'track-method');
      return;
    }

    if (proposition === 'sector') {
      const target = document.querySelector('[data-data-readiness]');
      insertAfter(target, fallbackSection({ key: 'sector-reference', title: 'Cổ phiếu tham chiếu theo ngành', description: 'Các nhóm dưới đây là phân loại của danh mục công khai hiện có, chưa phải bảng xếp hạng sức mạnh ngành.', body: sectorGrid(items), note: 'Khi dữ liệu giá đủ điều kiện, phần xếp hạng ngành phía trên mới được mở.' }), 'sector-reference');
      return;
    }

    if (proposition === 'ticker-search' || proposition === 'stock-search') {
      const target = document.querySelector('[data-data-readiness]') || document.querySelector('.search-panel');
      insertAfter(target, fallbackSection({ key: 'lookup-reference', title: `${items.length} mã tham chiếu có thể mở nhanh`, description: 'Chọn một mã để mở hồ sơ tra cứu. Mã ngoài danh sách này vẫn cần nguồn dữ liệu đầy đủ trước khi hệ thống xác nhận công khai.', body: referenceGrid(items), note: 'Danh sách tham chiếu dùng để tra cứu doanh nghiệp/ngành; không phải danh sách khuyến nghị.' }), 'lookup-reference');
      return;
    }

    if (proposition === 'stock-report') {
      const target = document.querySelector('[data-dynamic-stock-report]');
      insertAfter(target, fallbackSection({ key: 'report-reference', title: 'Mở nhanh một mã tham chiếu khác', description: 'Nếu báo cáo hiện tại chưa đủ dữ liệu, bạn vẫn có thể chuyển sang các mã HOSE đang có hồ sơ tham chiếu.', body: referenceGrid(items), note: 'Giá, định giá và tín hiệu chỉ xuất hiện khi lớp dữ liệu tương ứng đủ điều kiện.' }), 'report-reference');
    }
  }

  function enhanceNavigation() {
    const menu = document.querySelector('[data-nav-menu]');
    if (menu && ![...menu.querySelectorAll('a')].some(link => /dang-ky\/?$/.test(link.getAttribute('href') || ''))) {
      menu.insertAdjacentHTML('beforeend', '<a href="dang-ky/">Đăng ký</a>');
    }
    document.querySelectorAll('.footer-links').forEach(links => {
      const desired = [
        ['radar5/', 'Radar'], ['kiem-tra-co-phieu/', 'Tra cứu'], ['khuyen-nghi/', 'Khuyến nghị'],
        ['nganh/', 'Theo ngành'], ['hieu-qua/', 'Hiệu quả'], ['dang-ky/', 'Đăng ký'],
        ['dieu-khoan/', 'Điều khoản'], ['quyen-rieng-tu/', 'Quyền riêng tư']
      ];
      links.innerHTML = desired.map(([href, label]) => `<a href="${href}">${label}</a>`).join('');
    });
  }

  function sanitizeVisibleCopy(root = document.body) {
    if (!root) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => {
      const parent = node.parentElement;
      if (!parent || /^(SCRIPT|STYLE|NOSCRIPT|TEXTAREA)$/i.test(parent.tagName)) return;
      let value = node.nodeValue;
      copyReplacements.forEach((after, before) => {
        if (value.includes(before)) value = value.replaceAll(before, after);
      });
      if (value !== node.nodeValue) node.nodeValue = value;
    });
  }

  let observerScheduled = false;
  function observeDynamicCopy() {
    const observer = new MutationObserver(() => {
      if (observerScheduled) return;
      observerScheduled = true;
      requestAnimationFrame(() => {
        sanitizeVisibleCopy();
        enhanceNavigation();
        observerScheduled = false;
      });
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  }

  async function boot() {
    document.documentElement.classList.add('site-v4');
    enhanceNavigation();
    sanitizeVisibleCopy();
    observeDynamicCopy();
    if (!fallbackRoutes.has(proposition)) return;
    try {
      const payloadPath = routePayloadPath();
      const [master, payload] = await Promise.all([
        loadJson('public/data/ticker-universe.json'),
        payloadPath ? loadJson(payloadPath).catch(() => null) : Promise.resolve(null)
      ]);
      enhanceRoute(master, payload);
      sanitizeVisibleCopy();
    } catch (_) {
      // Fail closed: the primary page remains usable without inventing fallback data.
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})();
