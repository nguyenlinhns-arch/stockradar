(() => {
  'use strict';

  const DATA_URL = 'public/data/ticker-universe.json';
  const numberFormat = new Intl.NumberFormat('vi-VN');

  function text(target, value) {
    if (target) target.textContent = value;
  }

  function formatSnapshot(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '—';
    return new Intl.DateTimeFormat('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: 'Asia/Ho_Chi_Minh',
    }).format(date).replace(',', ' ·');
  }

  function sectorCounts(items) {
    const counts = new Map();
    items.forEach(item => {
      const sector = String(item.sector || 'Khác').trim() || 'Khác';
      counts.set(sector, (counts.get(sector) || 0) + 1);
    });
    return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'vi'));
  }

  function renderStats(root, payload) {
    const items = Array.isArray(payload.items) ? payload.items : [];
    const ref = payload.internal_reference || {};
    text(root.querySelector('[data-home-public-tickers]'), numberFormat.format(items.length));
    text(root.querySelector('[data-home-sectors]'), numberFormat.format(sectorCounts(items).length));
    text(root.querySelector('[data-home-reference-records]'), numberFormat.format(Number(ref.validated_count || ref.record_count || 0)));
    text(root.querySelector('[data-home-snapshot-time]'), formatSnapshot(payload.as_of || ref.as_of));
  }

  function renderSectors(root, items, activeSector = 'ALL') {
    const target = root.querySelector('[data-home-sector-chips]');
    if (!target) return;
    const sectors = sectorCounts(items);
    const chips = [['ALL', items.length], ...sectors];
    target.innerHTML = chips.map(([sector, count]) => {
      const label = sector === 'ALL' ? 'Tất cả' : sector;
      const active = sector === activeSector ? ' is-active' : '';
      return `<button class="market-sector-chip${active}" type="button" data-home-sector-filter="${sector}"><span>${label}</span><b>${count}</b></button>`;
    }).join('');
  }

  function tickerButton(item) {
    const ticker = String(item.ticker || '').toUpperCase();
    const company = String(item.company_name || '').trim();
    const sector = String(item.sector || '—').trim();
    return `<button class="market-stock-row" type="button" data-home-ticker="${ticker}" data-home-sector="${sector}">
      <span class="market-stock-symbol"><strong>${ticker}</strong><small>HOSE</small></span>
      <span class="market-stock-company">${company}</span>
      <span class="market-stock-sector">${sector}</span>
      <span class="market-stock-action">Tra cứu <span aria-hidden="true">→</span></span>
    </button>`;
  }

  function renderTable(root, items, activeSector = 'ALL') {
    const target = root.querySelector('[data-home-market-list]');
    const count = root.querySelector('[data-home-visible-count]');
    if (!target) return;
    const filtered = activeSector === 'ALL' ? items : items.filter(item => item.sector === activeSector);
    text(count, `${filtered.length} mã`);
    target.innerHTML = filtered.length
      ? filtered.map(tickerButton).join('')
      : '<div class="market-data-empty">Chưa có mã trong nhóm này.</div>';
  }

  function triggerLookup(ticker) {
    const form = document.querySelector('[data-stock-search-form]');
    const input = form?.querySelector('input[name="ticker"]');
    if (!form || !input) {
      window.location.href = 'kiem-tra-co-phieu/';
      return;
    }
    input.value = ticker;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    input.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  async function mount() {
    const root = document.querySelector('[data-home-market-data]');
    if (!root) return;
    const message = root.querySelector('[data-home-market-status]');

    try {
      const response = await fetch(DATA_URL, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      const items = Array.isArray(payload.items) ? payload.items : [];
      if (!items.length) throw new Error('EMPTY_REFERENCE_SET');

      renderStats(root, payload);
      renderSectors(root, items);
      renderTable(root, items);
      text(message, `Danh mục tham chiếu công khai · snapshot ${formatSnapshot(payload.as_of)} (GMT+7)`);

      root.addEventListener('click', event => {
        const filter = event.target.closest('[data-home-sector-filter]');
        if (filter) {
          const sector = filter.dataset.homeSectorFilter || 'ALL';
          renderSectors(root, items, sector);
          renderTable(root, items, sector);
          return;
        }
        const ticker = event.target.closest('[data-home-ticker]')?.dataset.homeTicker;
        if (ticker) triggerLookup(ticker);
      });
    } catch (_) {
      text(message, 'Dữ liệu tham chiếu tạm thời chưa tải được. Vui lòng thử lại sau.');
      const target = root.querySelector('[data-home-market-list]');
      if (target) target.innerHTML = '<div class="market-data-empty">Chưa thể tải danh mục tham chiếu.</div>';
    }
  }

  document.addEventListener('DOMContentLoaded', mount);
})();
