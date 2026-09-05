(() => {
  'use strict';
  const root = document.querySelector('[data-verified-recommendations]');
  if (!root) return;
  const search = root.querySelector('[data-verified-search]');
  const status = root.querySelector('[data-verified-status]');
  const rows = [...root.querySelectorAll('[data-verified-row]')];
  const count = root.querySelector('[data-verified-count]');
  count.setAttribute('aria-live', 'polite');
  function filter() {
    const ticker = search.value.trim().toUpperCase();
    const shown = new Set();
    for (const row of rows) {
      row.hidden = !((!ticker || row.dataset.ticker.includes(ticker)) && (!status.value || row.dataset.verifiedLifecycle === status.value));
      if (!row.hidden) shown.add(row.dataset.ticker);
    }
    root.querySelectorAll('[data-verified-detail],[data-verified-event]').forEach(el => {el.hidden = !shown.has(el.dataset.ticker);});
    count.textContent = `${shown.size} / ${rows.length} mã khuyến nghị`;
    root.querySelector('[data-verified-empty]').hidden = shown.size > 0;
  }
  search.addEventListener('input', filter);
  status.addEventListener('change', filter);
  root.querySelector('[data-verified-reset]').addEventListener('click', () => {search.value = '';status.value = '';filter();search.focus();});
  root.querySelector('[data-verified-controls]').disabled = false;
  root.addEventListener('click', event => {
    const link = event.target.closest('[data-rec-detail]');
    if (!link) return;
    const id = new URL(link.href).hash.slice(1);
    const detail = document.getElementById(id);
    if (!detail) return;
    event.preventDefault(); detail.open = true;
    history.replaceState(null, '', `#${id}`); detail.scrollIntoView({block:'start',behavior:'smooth'});
  });
  if (location.hash.startsWith('#history-')) {
    const detail = document.getElementById(location.hash.slice(1));
    if (detail) {detail.open = true;detail.scrollIntoView({block:'start'});}
  }
})();
