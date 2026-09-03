(() => {
  'use strict';

  const replacements = [
    ['CHƯA SẴN SÀNG', 'ĐANG CẬP NHẬT'],
    ['Chưa sẵn sàng', 'Đang cập nhật'],
    ['chưa sẵn sàng', 'đang cập nhật'],
    ['CHƯA PHÁT HÀNH', 'ĐANG CẬP NHẬT'],
    ['Chưa phát hành', 'Đang cập nhật'],
    ['chưa phát hành', 'đang cập nhật'],
    ['ĐANG KHÓA', 'ĐANG CẬP NHẬT'],
    ['CHƯA KẾT NỐI', 'ĐANG CẬP NHẬT'],
    ['CHƯA ĐỦ NGUỒN GIÁ', 'ĐANG CẬP NHẬT GIÁ'],
    ['CHƯA ĐỦ DỮ LIỆU', 'ĐANG CẬP NHẬT DỮ LIỆU'],
    ['TẠM CHƯA PHÁT HÀNH', 'ĐANG CẬP NHẬT'],
    ['Radar chưa phát hành thứ hạng khi nguồn giá chưa đạt điều kiện; danh sách tham chiếu vẫn được hiển thị cụ thể.', 'Radar cập nhật thứ hạng theo dữ liệu đạt chuẩn; danh sách cổ phiếu theo dõi vẫn hiển thị cụ thể.'],
    ['Chưa có cảnh báo hành động được phát hành ở dữ liệu công khai hiện tại.', 'Không có cảnh báo hành động tại dữ liệu công khai hiện tại.'],
    ['Khi chưa có khuyến nghị đã đóng, tỷ lệ thắng và lợi nhuận trung bình được để trống thay vì ước đoán.', 'Khi không có khuyến nghị đã đóng, tỷ lệ thắng và lợi nhuận trung bình được để trống thay vì ước đoán.'],
    ['Free: bản tin thị trường · Premium: TOP 30, phân tích chuyên sâu và cảnh báo hành động.', 'Free: tra cứu & nội dung công khai · Premium: báo cáo hằng ngày + cảnh báo hành động.'],
    ['Free: nhận bản rà soát thị trường cơ bản hằng ngày sau khi xác minh email và đồng ý nhận.', 'Free: tra cứu cổ phiếu và sử dụng nội dung công khai; chỉ nhận email hệ thống cần thiết cho tài khoản.'],
    ['Báo cáo StockRadar hằng ngày — bản rà soát thị trường cơ bản cho Free; nội dung sâu hơn khi tài khoản có quyền Premium.', 'Báo cáo StockRadar hằng ngày — dành cho tài khoản Premium; Free không nhận email báo cáo hằng ngày.'],
    ['Sau khi xác minh, bản tin Free đã đăng ký có thể được bật; cảnh báo mua/bán vẫn tuân theo quyền Premium.', 'Sau khi xác minh, tài khoản Free có thể dùng các tính năng công khai; email báo cáo và cảnh báo chỉ kích hoạt theo quyền Premium.'],
    ['TOP 30 + phân tích chuyên sâu + cảnh báo hành động', 'Top cổ phiếu + phân tích chuyên sâu + cảnh báo hành động'],
    ['TOP 30 StockRadar', 'Top cổ phiếu StockRadar'],
    ['TOP 30 STOCKRADAR', 'TOP CỔ PHIẾU STOCKRADAR'],
    ['[StockRadar Premium] TOP 30 HOSE', '[StockRadar Premium] Top cổ phiếu HOSE']
  ];

  function normalizeText(value) {
    let next = String(value || '');
    replacements.forEach(([before, after]) => {
      if (next.includes(before)) next = next.replaceAll(before, after);
    });
    return next;
  }

  function clean(root = document.body) {
    if (!root) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => {
      const parent = node.parentElement;
      if (!parent || /^(SCRIPT|STYLE|NOSCRIPT|TEXTAREA)$/i.test(parent.tagName)) return;
      const next = normalizeText(node.nodeValue);
      if (next !== node.nodeValue) node.nodeValue = next;
    });
  }

  function signupHref() {
    return new URL('signup/', document.baseURI).href;
  }

  function normalizeSignupLinks(root = document) {
    root.querySelectorAll?.('a[href]').forEach(link => {
      const raw = link.getAttribute('href') || '';
      if (/(^|\/)dang-ky\/?$/i.test(raw)) {
        link.setAttribute('href', raw.replace(/dang-ky\/?$/i, 'signup/'));
      }
    });
  }

  function redirectLegacySignup() {
    if (/\/dang-ky\/(?:index\.html)?$/i.test(window.location.pathname)) {
      window.location.replace(signupHref());
      return true;
    }
    return false;
  }

  function triggerTickerLookup(ticker) {
    const form = document.querySelector('[data-stock-search-form]');
    const input = form?.querySelector('input[name="ticker"]');
    if (!form || !input) {
      window.location.href = new URL(`kiem-tra-co-phieu/?ticker=${encodeURIComponent(ticker)}`, document.baseURI).href;
      return;
    }
    input.value = ticker;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    input.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function makeWatchlistInteractive() {
    document.querySelectorAll('.home-watch-row').forEach(row => {
      if (row.dataset.publicLookupReady === '1') return;
      const ticker = String(row.querySelector('b')?.textContent || '').trim().toUpperCase();
      if (!/^[A-Z]{3}$/.test(ticker)) return;
      row.dataset.publicLookupReady = '1';
      row.tabIndex = 0;
      row.setAttribute('role', 'button');
      row.setAttribute('aria-label', `Tra cứu ${ticker}`);
      const activate = () => triggerTickerLookup(ticker);
      row.addEventListener('click', activate);
      row.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          activate();
        }
      });
    });
  }

  function ensureHomePolish() {
    if (!document.body?.classList.contains('app-home')) return;
    if (document.querySelector('style[data-stockradar-home-polish]')) return;
    const style = document.createElement('style');
    style.dataset.stockradarHomePolish = '';
    style.textContent = `
      .app-home .home-watch-row[data-public-lookup-ready="1"]{cursor:pointer;transition:background .15s ease,box-shadow .15s ease}
      .app-home .home-watch-row[data-public-lookup-ready="1"]:hover{background:#f4f8fb}
      .app-home .home-watch-row[data-public-lookup-ready="1"]:focus-visible{outline:2px solid #1f6fae;outline-offset:-2px;background:#f4f8fb}
      .app-home .home-register-compact span{max-width:52ch}
      .app-home .home-status-grid strong{font-size:12px}
      @media(max-width:560px){.app-home .home-status-grid strong{font-size:11px}.app-home .home-watch-row{min-height:42px}}
    `;
    document.head.append(style);
  }

  function optimizeHomepage() {
    if (!document.body?.classList.contains('app-home')) return;

    ensureHomePolish();

    const pill = document.querySelector('.operations-title-row .data-pill');
    if (pill) pill.textContent = 'HOSE · 4 KHUNG ĐẦU TƯ';

    const register = document.querySelector('.home-register-compact');
    if (register) {
      const heading = register.querySelector('strong');
      const description = register.querySelector('span');
      const action = register.querySelector('a');
      if (heading) heading.textContent = 'StockRadar Premium';
      if (description) description.textContent = 'Free: tra cứu & nội dung công khai · Premium: báo cáo hằng ngày + cảnh báo hành động.';
      if (action) {
        action.textContent = 'Đăng ký';
        action.href = signupHref();
      }
    }

    const statusItems = [...document.querySelectorAll('.home-status-grid article')];
    const statusCopy = [
      ['Phạm vi', 'HOSE'],
      ['Khung đầu tư', '4 chiến lược'],
      ['Tín hiệu', 'Chỉ khi đạt chuẩn'],
      ['Quản trị', 'Buy Zone · Stop · Target'],
      ['Premium', 'Email & cảnh báo hành động']
    ];
    statusItems.forEach((item, index) => {
      const copy = statusCopy[index];
      if (!copy) return;
      const label = item.querySelector('span');
      const value = item.querySelector('strong');
      if (label) label.textContent = copy[0];
      if (value) value.textContent = copy[1];
    });

    const recommendation = document.querySelector('.home-recommendation-panel');
    if (recommendation) {
      const summary = recommendation.querySelectorAll('.home-recommendation-summary > div');
      const firstNote = summary[0]?.querySelector('small');
      const secondNote = summary[1]?.querySelector('small');
      if (firstNote) firstNote.textContent = 'Chỉ hiển thị khi setup đạt chuẩn hành động.';
      if (secondNote) secondNote.textContent = '16 mã hiển thị nhanh; tra cứu các mã HOSE khác ở ô tìm kiếm.';
      const watchNote = recommendation.querySelector('.home-watch-note');
      if (watchNote) watchNote.textContent = 'Khi có tín hiệu: Setup · Buy Zone · Tỷ trọng · Stop · Target · Upside/Downside · R:R.';
    }

    const sectorDescription = document.querySelector('.home-sector-panel .home-panel-head p');
    if (sectorDescription) sectorDescription.textContent = 'Các nhóm đang hiển thị nhanh trên HOSE.';

    document.querySelector('.home-ticker-strip')?.remove();
    document.querySelector('.premium-preview-section')?.remove();

    const mobileBar = document.querySelector('.mobile-newsletter-bar');
    if (mobileBar) {
      const label = mobileBar.querySelector('span');
      const action = mobileBar.querySelector('a');
      if (label) label.textContent = 'Premium: báo cáo hằng ngày + cảnh báo hành động';
      if (action) {
        action.textContent = 'Đăng ký';
        action.href = signupHref();
      }
    }

    makeWatchlistInteractive();
  }

  function applyPublicUx() {
    if (redirectLegacySignup()) return;
    clean();
    normalizeSignupLinks();
    optimizeHomepage();
  }

  let scheduled = false;
  const scheduleClean = () => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      clean();
      normalizeSignupLinks();
      if (document.body?.classList.contains('app-home')) makeWatchlistInteractive();
      scheduled = false;
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      applyPublicUx();
      if (document.body) new MutationObserver(scheduleClean).observe(document.body, { childList: true, subtree: true, characterData: true });
    }, { once: true });
  } else {
    applyPublicUx();
    if (document.body) new MutationObserver(scheduleClean).observe(document.body, { childList: true, subtree: true, characterData: true });
  }
})();