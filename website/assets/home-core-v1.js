(() => {
  'use strict';

  function emailDeliveryReady() {
    return window.STOCKRADAR_AUTH_CONFIG?.emailDeliveryReady === true;
  }

  function normalizeTicker(value) {
    return String(value || '').trim().toUpperCase().replace(/[^A-Z]/g, '').slice(0, 3);
  }

  function validTicker(value) {
    return /^[A-Z]{3}$/.test(value);
  }

  function stockUrl(ticker) {
    return new URL(`co-phieu/?ticker=${encodeURIComponent(ticker)}`, document.baseURI).href;
  }

  function registrationUrl() {
    return new URL('dang-ky/', document.baseURI).href;
  }

  function setSearchMessage(form, message, kind = '') {
    const target = form?.parentElement?.querySelector('[data-stock-search-result]');
    if (!target) return;
    target.className = `search-result${kind ? ` ${kind}` : ''}`;
    target.textContent = message;
  }

  function mountNavigation() {
    const toggle = document.querySelector('[data-nav-toggle]');
    const menu = document.querySelector('[data-nav-menu]');
    if (!toggle || !menu) return;

    const close = () => {
      menu.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
    };
    const open = () => {
      menu.classList.add('is-open');
      toggle.setAttribute('aria-expanded', 'true');
    };

    toggle.addEventListener('click', event => {
      event.stopPropagation();
      menu.classList.contains('is-open') ? close() : open();
    });
    document.addEventListener('click', event => {
      if (!menu.contains(event.target) && !toggle.contains(event.target)) close();
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') close();
    });
    menu.addEventListener('click', event => {
      if (event.target.closest('a')) close();
    });
  }

  function mountTickerSearch() {
    document.querySelectorAll('[data-stock-search-form]').forEach(form => {
      const input = form.querySelector('input[name="ticker"]');
      if (!input) return;
      input.addEventListener('input', () => {
        const normalized = normalizeTicker(input.value);
        if (input.value !== normalized) input.value = normalized;
        setSearchMessage(form, '');
      });
      form.addEventListener('submit', event => {
        event.preventDefault();
        const ticker = normalizeTicker(input.value);
        input.value = ticker;
        if (!validTicker(ticker)) {
          setSearchMessage(form, 'Nhập mã gồm đúng 3 chữ cái, ví dụ FPT.', 'error');
          input.focus();
          return;
        }
        window.location.assign(stockUrl(ticker));
      });
    });
  }

  function mountRegistration() {
    const href = registrationUrl();
    document.querySelectorAll('a[href]').forEach(link => {
      let parsed;
      try { parsed = new URL(link.getAttribute('href') || '', document.baseURI); } catch (_) { return; }
      const path = parsed.pathname.replace(/\/+$/, '');
      if (!/(?:\/signup|\/dang-ky)$/.test(path)) return;
      link.href = href;
      if (link.classList.contains('header-register-cta')) {
        link.textContent = 'Đăng ký';
        link.setAttribute('aria-label', 'So sánh gói Free và Premium StockRadar');
      }
    });

    const compact = document.querySelector('.home-register-compact');
    if (compact) {
      const text = compact.querySelector('span');
      const action = compact.querySelector('a');
      if (text) text.textContent = 'Free: tra cứu và theo dõi · Premium: phân tích sâu, email và cảnh báo hành động.';
      if (action) action.textContent = 'So sánh gói';
    }

    const mobile = document.querySelector('.mobile-newsletter-bar a');
    if (mobile) mobile.textContent = 'Xem gói';

    emailDeliveryReady();
  }

  function mount() {
    mountNavigation();
    mountTickerSearch();
    mountRegistration();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();