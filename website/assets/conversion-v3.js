(() => {
  'use strict';

  const params = new URLSearchParams(window.location.search);
  const body = document.body;

  function withTicker(href) {
    const ticker = (params.get('ticker') || '').trim().toUpperCase();
    if (!ticker) return href;
    try {
      const url = new URL(href, window.location.href);
      url.searchParams.set('ticker', ticker);
      return url.pathname.replace(/^\//, '') + (url.search ? url.search : '') + (url.hash || '');
    } catch (_) {
      return href;
    }
  }

  document.querySelectorAll('[data-premium-conversion-cta]').forEach((link) => {
    const href = link.getAttribute('href');
    if (href) link.setAttribute('href', withTicker(href));
  });

  const isSignup = body && body.dataset.proposition === 'account' && /\/signup\/?$/.test(window.location.pathname);
  if (isSignup && params.get('plan') === 'premium') {
    body.classList.add('conversion-premium-flow');
    const premium = document.querySelector('input[name="selected_plan"][value="premium"]');
    if (premium) {
      premium.checked = true;
      premium.dispatchEvent(new Event('change', { bubbles: true }));
    }
    const summary = document.querySelector('[data-premium-flow-summary]');
    if (summary) summary.hidden = false;
    const titleName = document.querySelector('[data-signup-plan-name]');
    if (titleName) titleName.textContent = 'Premium';
    const submit = document.querySelector('[data-signup-submit-label]');
    if (submit) submit.textContent = 'Tạo tài khoản Premium & gửi mã xác minh';
  }

  document.querySelectorAll('[data-conversion-action]').forEach((el) => {
    el.addEventListener('click', () => {
      try {
        sessionStorage.setItem('stockradar:last_conversion_action', el.getAttribute('data-conversion-action') || '');
      } catch (_) {
        // Session storage is optional; conversion behavior must never depend on it.
      }
    });
  });
})();
