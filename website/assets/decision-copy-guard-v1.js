(() => {
  'use strict';

  const exactReplacements = [
    ['4M · CANSLIM · Payback', 'Dữ liệu doanh nghiệp'],
    ['4M · Payback · CANSLIM', 'Dữ liệu doanh nghiệp'],
    ['4M · CANSLIM', 'Dữ liệu doanh nghiệp'],
    ['SEPA/VCP · Stage · Pivot', 'Trạng thái giá · Mốc hành động'],
    ['SEPA · VCP · Stage · VPA', 'Xu hướng · Dòng tiền'],
    ['SEPA · VCP · VPA · RVOL', 'Xu hướng · Dòng tiền · Khối lượng giao dịch'],
    ['VPA · RVOL · dòng tiền lớn', 'Dòng tiền · Khối lượng giao dịch'],
    ['Pocket Pivot · Early Breakout · Confirmed Breakout · Retest', 'Mua · chờ · theo dõi · bỏ qua'],
    ['Pocket Pivot · Early Breakout · Confirmed Breakout', 'Mua · chờ · theo dõi'],
    ['Pocket Pivot · Breakout · Retest', 'Mua · chờ · theo dõi · bỏ qua'],
    ['Bear / Base / Bull', 'Thận trọng / Cơ sở / Tích cực'],
    ['Bear · Base · Bull', 'Thận trọng · Cơ sở · Tích cực'],
    ['Bear/Base/Bull', 'Thận trọng/Cơ sở/Tích cực'],
  ];

  const wordReplacements = [
    [/phân tích/giu, 'tra cứu'],
    [/phương pháp/giu, 'cách dùng'],
    [/setup/giu, 'trạng thái'],
    [/CANSLIM/gu, 'Tăng trưởng'],
    [/SEPA/gu, 'Xu hướng'],
    [/VCP/gu, 'Nền giá'],
    [/VPA/gu, 'Dòng tiền'],
    [/RVOL/gu, 'Khối lượng so với mức trung bình'],
    [/Pocket Pivot/giu, 'Điểm mua sớm'],
    [/Early Breakout/giu, 'Điểm mua sớm'],
    [/Confirmed Breakout/giu, 'Điểm mua xác nhận'],
    [/Breakout/giu, 'Điểm mua'],
    [/Retest/giu, 'Kiểm tra lại vùng giá'],
    [/Payback/giu, 'Hoàn vốn'],
    [/Wyckoff/giu, 'Dòng tiền'],
    [/Minervini/giu, 'Xu hướng'],
    [/(?:William J\.\s*)?O[’']Neil/giu, 'Tăng trưởng'],
    [/Phil Town/giu, 'Doanh nghiệp'],
    [/Gil Morales/giu, 'Điểm mua'],
    [/Chris Kacher/giu, 'Điểm mua'],
    [/Ichimoku/giu, 'Xu hướng'],
    [/Bollinger(?: Bands)?/giu, 'Biến động giá'],
    [/Trendline/giu, 'Xu hướng'],
    [/\bStage\b/giu, 'Xu hướng'],
    [/\bPivot\b/giu, 'Mốc giá'],
    [/\b4M\b/gu, 'Doanh nghiệp'],
  ];

  function normalize(value) {
    let next = String(value || '');
    exactReplacements.forEach(([before, after]) => {
      if (next.includes(before)) next = next.replaceAll(before, after);
    });
    wordReplacements.forEach(([pattern, after]) => {
      next = next.replace(pattern, after);
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
      if (!parent || /^(SCRIPT|STYLE|NOSCRIPT|TEXTAREA|CODE|PRE)$/i.test(parent.tagName)) return;
      const next = normalize(node.nodeValue);
      if (next !== node.nodeValue) node.nodeValue = next;
    });

    root.querySelectorAll?.('[aria-label],[title]').forEach(node => {
      for (const attr of ['aria-label', 'title']) {
        const value = node.getAttribute(attr);
        if (!value) continue;
        const next = normalize(value);
        if (next !== value) node.setAttribute(attr, next);
      }
    });
  }

  let scheduled = false;
  const schedule = () => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      clean(document.body);
      scheduled = false;
    });
  };

  const start = () => {
    clean(document.body);
    if (document.body) {
      new MutationObserver(schedule).observe(document.body, {
        childList: true,
        subtree: true,
        characterData: true,
        attributes: true,
        attributeFilter: ['aria-label', 'title'],
      });
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();