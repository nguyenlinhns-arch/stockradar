(() => {
  'use strict';

  const replacements = [
    ['Danh sách cổ phiếu đang theo dõi', 'Danh sách cổ phiếu theo Radar rà soát'],
    ['Mã tham chiếu đang theo dõi', 'Danh sách cổ phiếu theo Radar rà soát'],
    ['danh sách cổ phiếu theo dõi', 'danh sách cổ phiếu theo Radar rà soát'],
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
    ['Radar chưa phát hành thứ hạng khi nguồn giá chưa đạt điều kiện; danh sách tham chiếu vẫn được hiển thị cụ thể.', 'Radar rà soát danh sách cổ phiếu cân bằng theo ngành và cập nhật trạng thái theo dữ liệu đạt chuẩn.'],
    ['Chưa có cảnh báo hành động được phát hành ở dữ liệu công khai hiện tại.', 'Không có cảnh báo hành động tại dữ liệu công khai hiện tại.'],
    ['Khi chưa có khuyến nghị đã đóng, tỷ lệ thắng và lợi nhuận trung bình được để trống thay vì ước đoán.', 'Khi không có khuyến nghị đã đóng, tỷ lệ thắng và lợi nhuận trung bình được để trống thay vì ước đoán.']
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

  let scheduled = false;
  const scheduleClean = () => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      clean();
      scheduled = false;
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      clean();
      new MutationObserver(scheduleClean).observe(document.body, { childList: true, subtree: true, characterData: true });
    }, { once: true });
  } else {
    clean();
    new MutationObserver(scheduleClean).observe(document.body, { childList: true, subtree: true, characterData: true });
  }
})();
