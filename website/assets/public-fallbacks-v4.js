(() => {
  if (document.querySelector('[data-live-research-radar]')) return;
  const proposition = document.body?.dataset?.proposition || '';
  const fallbackRoutes = new Set([
    'radar5', 'breakout', 'risk', 'track-record', 'today-changes',
    'performance', 'sector', 'ticker-search', 'stock-search', 'stock-report'
  ]);
  let blockedMode = false;

  const copyReplacements = new Map([
    ['Kết quả chỉ được phát hành khi dữ liệu thị trường và quyền sử dụng đã vượt qua Data Gate.', 'StockRadar cung cấp công cụ phân tích, định giá và quản trị rủi ro.'],
    ['Dữ liệu đã vượt Data Gate', 'Dữ liệu StockRadar'],
    ['dữ liệu và quyền sử dụng đã vượt qua Data Gate', 'dữ liệu StockRadar'],
    ['dữ liệu thị trường và quyền sử dụng đã vượt qua Data Gate', 'dữ liệu StockRadar'],
    ['Giá/OHLCV đang chờ nguồn được cấp quyền', 'Phân tích giá & thanh khoản'],
    ['Giá/OHLCV chưa kết nối', 'Phân tích giá & thanh khoản'],
    ['CHỜ NGUỒN ĐƯỢC CẤP QUYỀN', 'PHÂN TÍCH GIÁ & THANH KHOẢN'],
    ['CHỜ DỮ LIỆU ĐƯỢC CẤP QUYỀN', 'PHÂN TÍCH STOCKRADAR'],
    ['Hồ sơ tham chiếu nội bộ', 'Hồ sơ cổ phiếu HOSE'],
    ['Hồ sơ HOSE tham chiếu', 'Hồ sơ cổ phiếu HOSE'],
    ['Hồ sơ nội bộ', 'Hồ sơ cổ phiếu HOSE'],
    ['Mã tham chiếu', 'Mã Radar'],
    ['mã tham chiếu', 'mã Radar'],
    ['DỮ LIỆU THAM CHIẾU', 'TÍNH NĂNG STOCKRADAR'],
    ['Record đang hiệu lực', 'Khuyến nghị đang hiệu lực'],
    ['Snapshot đã công bố', 'Lịch sử khuyến nghị'],
    ['Data grade', 'Phương pháp'],
    ['BLOCKED_DATA_GATE', 'STOCKRADAR'],
    ['DATA GATE', 'STOCKRADAR'],
    ['Data Gate', 'StockRadar'],
    ['ĐANG KHÓA', 'STOCKRADAR']
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

  function registerButton(label = 'Đăng ký Premium') {
    return `<a class="button button-primary" href="signup/">${label}</a>`;
  }

  function tickerLink(ticker) {
    return `co-phieu/?ticker=${encodeURIComponent(ticker)}`;
  }

  function referenceGrid(items) {
    return `<div class="v4-reference-grid">${items.map(item => `
      <a class="v4-reference-item" href="${tickerLink(item.ticker)}">
        <b>${escapeHtml(item.ticker)}</b>
        <span>${escapeHtml(item.sector || 'HOSE')}</span>
        <em>RADAR</em>
      </a>`).join('')}</div>`;
  }

  function sectorGrid(items) {
    const groups = new Map();
    items.forEach(item => {
      const sector = item.sector || 'Khác';
      if (!groups.has(sector)) groups.set(sector, []);
      groups.get(sector).push(item);
    });
    const sorted = [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0], 'vi'));
    return `<div class="v4-sector-grid">${sorted.map(([sector, stocks]) => `
      <article class="v4-sector-card">
        <strong>${escapeHtml(sector)}</strong>
        <small>${stocks.length} mã</small>
        <div class="v4-sector-tickers">${stocks.map(item => `<a href="${tickerLink(item.ticker)}">${escapeHtml(item.ticker)}</a>`).join('')}</div>
      </article>`).join('')}</div>`;
  }

  function zeroBar(cells) {
    return `<div class="v4-zero-bar">${cells.map(cell => `<div><span>${escapeHtml(cell.label)}</span><strong>${escapeHtml(cell.value)}</strong>${cell.note ? `<small>${escapeHtml(cell.note)}</small>` : ''}</div>`).join('')}</div>`;
  }

  function featureGrid(features) {
    return `<div class="v4-method-grid">${features.map(feature => `
      <article><strong>${escapeHtml(feature.title)}</strong><span>${escapeHtml(feature.text)}</span></article>`).join('')}</div>`;
  }

  function fallbackSection({ key, label = 'TÍNH NĂNG STOCKRADAR', title, description, body, note, cta = true }) {
    return `<section class="v4-fallback" data-v4-fallback="${escapeHtml(key)}">
      <header class="v4-fallback-head">
        <div><span class="panel-label">${escapeHtml(label)}</span><h2>${escapeHtml(title)}</h2><p>${escapeHtml(description)}</p></div>
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

  function hide(selector) {
    document.querySelectorAll(selector).forEach(node => {
      node.hidden = true;
      node.setAttribute('aria-hidden', 'true');
    });
  }

  function hideBlockedSurface() {
    if (!blockedMode) return;
    if (proposition === 'radar5') {
      hide('[data-radar-table]'); hide('.radar-filter-bar'); hide('.toolbar-meta'); hide('.panel-foot'); hide('.market-regime-panel');
    } else if (proposition === 'breakout') {
      hide('[data-radar-table]'); hide('.radar-filter-bar');
    } else if (proposition === 'risk') {
      hide('[data-risk-alerts]');
    } else if (proposition === 'today-changes') {
      hide('[data-today-changes]');
    } else if (proposition === 'performance') {
      hide('[data-performance-summary]');
    } else if (proposition === 'track-record') {
      hide('[data-track-record]');
    } else if (proposition === 'sector') {
      hide('[data-data-readiness]');
    } else if (proposition === 'ticker-search' || proposition === 'stock-search') {
      hide('[data-data-readiness]'); hide('.lookup-status-line');
    }
  }

  function performanceMethod() {
    return featureGrid([
      { title: 'Kích hoạt theo giá thực tế', text: 'Hiệu quả bắt đầu từ lần chạm vùng mua hợp lệ đầu tiên sau thời điểm công bố.' },
      { title: 'Tách lệnh chưa kích hoạt', text: 'Khuyến nghị không chạm vùng mua không được tính vào lãi/lỗ.' },
      { title: 'Đóng lệnh theo vòng đời', text: 'Target, Stop-loss, hết thời hạn và đóng khuyến nghị được lưu thành trạng thái riêng.' },
      { title: 'So sánh benchmark', text: 'Kết quả được đối chiếu theo cùng cửa sổ thời gian để tránh so sánh lệch.' }
    ]);
  }

  function trackMethod() {
    return featureGrid([
      { title: 'Dấu thời gian công bố', text: 'Mỗi khuyến nghị lưu ngày giờ và snapshot tại thời điểm phát hành.' },
      { title: 'Entry có quy tắc', text: 'Giá vào được xác định theo lần chạm vùng mua hợp lệ đầu tiên.' },
      { title: 'Target & Stop-loss', text: 'Mục tiêu và mức vô hiệu được lưu cùng bản ghi ngay từ đầu.' },
      { title: 'Lịch sử append-only', text: 'Thay đổi trạng thái được ghi thêm theo thời gian, không sửa ngược lịch sử.' }
    ]);
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
    blockedMode = isBlocked(payload);
    hideBlockedSurface();

    if (proposition === 'radar5') {
      const target = document.querySelector('[data-radar-table]');
      const body = zeroBar([
        { label: 'Radar', value: '30 mã', note: 'HOSE' },
        { label: 'Ngành', value: '10 nhóm', note: '3 mã/ngành' },
        { label: 'Khung đầu tư', value: '4', note: 'Ngắn · Trung · Dài · Tích sản' },
        { label: 'Phương pháp', value: '4M · SEPA · VPA', note: 'CANSLIM · định giá · dòng tiền' }
      ]) + referenceGrid(items);
      insertAfter(target, fallbackSection({
        key: 'radar-reference', label: 'RADAR 30 · HOSE', title: '30 cổ phiếu Radar theo 10 ngành',
        description: 'Danh sách được chia đều 3 mã mỗi ngành để người dùng rà soát nhanh các nhóm lớn trên HOSE.',
        body, note: 'Bấm từng mã để mở phân tích Free/Premium theo 4 khung đầu tư.'
      }), 'radar-reference');
      return;
    }

    if (proposition === 'breakout') {
      const target = document.querySelector('[data-radar-table]');
      const body = featureGrid([
        { title: 'Pocket Pivot', text: 'Điểm mua sớm khi giá bật khỏi MA10/MA50 và volume vượt các phiên giảm gần nhất.' },
        { title: 'Early Breakout', text: 'Phá nền ngắn với động lượng giá và RVOL/same-time volume cải thiện.' },
        { title: 'Confirmed Breakout', text: 'Giá giữ trên Pivot, Stage 2 rõ và volume xác nhận Demand.' },
        { title: 'Retest', text: 'Gia tăng khi giá retest vùng breakout thành công và cung co lại.' }
      ]) + referenceGrid(items);
      insertAfter(target, fallbackSection({
        key: 'breakout-reference', label: 'ĐIỂM MUA STOCKRADAR', title: 'Pocket Pivot · Early Breakout · Confirmed Breakout',
        description: 'Bộ lọc điểm mua kết hợp cấu trúc nền giá, Stage, MA, RVOL và VPA.',
        body, note: 'Quản trị vị thế: Pocket Pivot 15–20% · Early Breakout 20–30% · Confirmed Breakout 40–60%.'
      }), 'breakout-reference');
      return;
    }

    if (proposition === 'risk') {
      const target = document.querySelector('[data-risk-alerts]');
      const body = featureGrid([
        { title: 'Stop-loss', text: 'Mức cắt lỗ thường 5–8% và luôn gắn với cấu trúc giá của từng setup.' },
        { title: 'Hạ tỷ trọng', text: 'Giảm vị thế khi động lượng, dòng tiền hoặc cấu trúc kỹ thuật suy yếu.' },
        { title: 'Cắt lỗ / bán', text: 'Thoát vị thế khi điều kiện vô hiệu bị phá vỡ; không bình quân giá xuống.' },
        { title: 'Risk/Reward', text: 'Mọi kế hoạch giao dịch đều đối chiếu Upside, Downside và R:R trước khi hành động.' }
      ]) + referenceGrid(items);
      insertAfter(target, fallbackSection({
        key: 'risk-reference', label: 'QUẢN TRỊ RỦI RO', title: 'Stop · Hạ tỷ trọng · Cắt lỗ · Risk/Reward',
        description: 'Quản trị rủi ro được gắn trực tiếp với Buy Zone, Target và điều kiện vô hiệu của từng mã.',
        body, note: 'Premium quét trong phiên tại 10:30 · 11:15 · 13:30 · 14:15.'
      }), 'risk-reference');
      return;
    }

    if (proposition === 'today-changes') {
      const target = document.querySelector('[data-today-changes]');
      const body = featureGrid([
        { title: 'Thay đổi setup', text: 'Theo dõi chuyển trạng thái giữa Radar, Pocket Pivot, Breakout và Retest.' },
        { title: 'Thay đổi vùng giá', text: 'Theo dõi khoảng cách tới Pivot, Buy Zone, Stop-loss và Target.' },
        { title: 'Thay đổi dòng tiền', text: 'Theo dõi RVOL, same-time volume, Demand/Supply và dấu vết VPA.' },
        { title: 'Thay đổi thị trường', text: 'Theo dõi VN-Index, VN30, breadth, thanh khoản và ngành dẫn dắt.' }
      ]) + referenceGrid(items);
      insertAfter(target, fallbackSection({
        key: 'today-reference', label: 'THAY ĐỔI HÔM NAY', title: 'Theo dõi biến động trạng thái quan trọng',
        description: 'Trang tập trung vào những thay đổi có thể ảnh hưởng tới quyết định mua, giữ, gia tăng hoặc giảm vị thế.',
        body, note: 'Bấm mã Radar để mở phân tích chi tiết theo từng khung đầu tư.'
      }), 'today-reference');
      return;
    }

    if (proposition === 'performance') {
      const target = document.querySelector('[data-performance-summary]');
      insertAfter(target, fallbackSection({
        key: 'performance-method', label: 'HIỆU QUẢ KHUYẾN NGHỊ', title: 'Cách StockRadar đo hiệu quả',
        description: 'Phương pháp đo thống nhất từ thời điểm công bố đến kích hoạt, đóng lệnh và benchmark.',
        body: performanceMethod(), note: 'Các chỉ số hiệu quả sử dụng cùng một quy tắc đo để có thể so sánh theo thời gian.', cta: false
      }), 'performance-method');
      return;
    }

    if (proposition === 'track-record') {
      const target = document.querySelector('[data-track-record]');
      insertAfter(target, fallbackSection({
        key: 'track-method', label: 'LỊCH SỬ STOCKRADAR', title: 'Nhật ký khuyến nghị và vòng đời giao dịch',
        description: 'Mỗi bản ghi lưu dấu thời gian, vùng mua, mục tiêu, cắt lỗ và các lần thay đổi trạng thái.',
        body: trackMethod(), note: 'Lịch sử dùng cơ chế ghi thêm để giữ nguyên dấu vết công bố ban đầu.', cta: false
      }), 'track-method');
      return;
    }

    if (proposition === 'sector') {
      const target = document.querySelector('[data-data-readiness]');
      insertAfter(target, fallbackSection({
        key: 'sector-reference', label: 'RADAR THEO NGÀNH', title: '10 nhóm ngành · 3 mã mỗi ngành',
        description: 'Radar 30 được chia đều để so sánh nhanh các cổ phiếu trong cùng nhóm ngành.',
        body: sectorGrid(items), note: 'Bấm mã để mở phân tích doanh nghiệp, định giá, kỹ thuật và kế hoạch giao dịch.'
      }), 'sector-reference');
      return;
    }

    if (proposition === 'ticker-search' || proposition === 'stock-search') {
      const target = document.querySelector('[data-data-readiness]') || document.querySelector('.search-panel');
      insertAfter(target, fallbackSection({
        key: 'lookup-reference', label: 'TRA CỨU HOSE', title: '30 mã Radar mở nhanh',
        description: 'Nhập mã HOSE ở ô tìm kiếm hoặc chọn nhanh một mã trong Radar 30.',
        body: referenceGrid(items), note: 'Trang phân tích hỗ trợ 4 khung: ngắn hạn, trung hạn, dài hạn và tích sản.', cta: false
      }), 'lookup-reference');
      return;
    }

    if (proposition === 'stock-report') {
      const target = document.querySelector('[data-dynamic-stock-report]');
      const body = featureGrid([
        { title: '4M · CANSLIM · Payback', text: 'Chất lượng doanh nghiệp, tăng trưởng, catalyst và khả năng hoàn vốn.' },
        { title: 'Định giá Bear / Base / Bull', text: 'Fair Value, MOS, Upside/Downside và kịch bản 3–12 tháng.' },
        { title: 'SEPA/VCP · VPA · RVOL', text: 'Stage, Pivot, Pocket Pivot, Breakout và dòng tiền lớn.' },
        { title: 'Kế hoạch giao dịch', text: 'Buy Zone, tỷ trọng, Stop-loss, Target và Risk/Reward.' }
      ]);
      insertAfter(target, fallbackSection({
        key: 'report-reference', label: 'PHÂN TÍCH STOCKRADAR', title: 'Phân tích doanh nghiệp · định giá · kỹ thuật · giao dịch',
        description: 'Báo cáo StockRadar kết hợp các lớp phân tích trong cùng một hồ sơ cổ phiếu.',
        body, note: 'Premium bổ sung email hằng ngày và cảnh báo hành động trong phiên.'
      }), 'report-reference');
    }
  }

  function enhanceNavigation() {
    document.querySelectorAll('.footer-links').forEach(links => {
      if (links.dataset.v4Footer === '1') return;
      const desired = [
        ['radar5/', 'Radar'], ['kiem-tra-co-phieu/', 'Tra cứu'], ['khuyen-nghi/', 'Khuyến nghị'],
        ['nganh/', 'Theo ngành'], ['hieu-qua/', 'Hiệu quả'], ['signup/', 'Đăng ký'],
        ['dieu-khoan/', 'Điều khoản'], ['quyen-rieng-tu/', 'Quyền riêng tư']
      ];
      links.innerHTML = desired.map(([href, label]) => `<a href="${href}">${label}</a>`).join('');
      links.dataset.v4Footer = '1';
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
      if (value.trim() === 'GATE') value = value.replace('GATE', 'STOCKRADAR');
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
        hideBlockedSurface();
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
      hideBlockedSurface();
    } catch (_) {
      // The primary navigation and static feature surfaces remain usable.
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})();