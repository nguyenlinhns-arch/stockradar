(() => {
  'use strict';

  const params = new URLSearchParams(window.location.search);
  const body = document.body;
  const FALLBACK_SUPABASE_URL = 'https://xamviatbxufjlpiwhebb.supabase.co';
  const SESSION_KEY = 'sr_conversion_session_v1';
  const TICKER_KEY = 'sr_conversion_ticker_v1';
  const PAGE_SEEN_PREFIX = 'sr_conversion_seen_v1:';

  function endpoint() {
    const authConfig = window.STOCKRADAR_AUTH_CONFIG || {};
    const base = authConfig.supabaseUrl || FALLBACK_SUPABASE_URL;
    return `${String(base).replace(/\/$/, '')}/functions/v1/conversion-event`;
  }

  function anonymousSessionId() {
    try {
      let value = sessionStorage.getItem(SESSION_KEY) || '';
      if (!/^[A-Za-z0-9_-]{16,80}$/.test(value)) {
        value = crypto.randomUUID
          ? crypto.randomUUID()
          : `${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}_${Math.random().toString(36).slice(2)}`;
        sessionStorage.setItem(SESSION_KEY, value);
      }
      return value;
    } catch (_) {
      return `${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}_${Math.random().toString(36).slice(2)}`;
    }
  }

  function currentTicker() {
    const fromQuery = String(params.get('ticker') || '').trim().toUpperCase();
    if (/^[A-Z0-9]{3}$/.test(fromQuery)) return fromQuery;
    const staticTicker = String(document.querySelector('[data-static-ticker]')?.dataset.staticTicker || '').trim().toUpperCase();
    if (/^[A-Z0-9]{3}$/.test(staticTicker)) return staticTicker;
    try {
      const remembered = String(sessionStorage.getItem(TICKER_KEY) || '').trim().toUpperCase();
      return /^[A-Z0-9]{3}$/.test(remembered) ? remembered : '';
    } catch (_) {
      return '';
    }
  }

  function rememberTicker(value) {
    const ticker = String(value || '').trim().toUpperCase();
    if (!/^[A-Z0-9]{3}$/.test(ticker)) return;
    try { sessionStorage.setItem(TICKER_KEY, ticker); } catch (_) {}
  }

  function currentPlan() {
    const fromQuery = String(params.get('plan') || '').trim().toUpperCase();
    if (fromQuery === 'FREE' || fromQuery === 'PREMIUM') return fromQuery;
    const selected = String(document.querySelector('input[name="selected_plan"]:checked')?.value || '').trim().toUpperCase();
    return selected === 'FREE' || selected === 'PREMIUM' ? selected : '';
  }

  function attribution() {
    let referrerHost = '';
    try { referrerHost = document.referrer ? new URL(document.referrer).hostname : ''; } catch (_) {}
    return {
      utm_source: String(params.get('utm_source') || '').slice(0, 120),
      utm_campaign: String(params.get('utm_campaign') || '').slice(0, 160),
      referrer_host: String(referrerHost || '').slice(0, 253),
    };
  }

  function sendEvent(eventName, extra = {}, options = {}) {
    const ticker = String(extra.ticker || currentTicker() || '').trim().toUpperCase();
    const plan = String(extra.plan_interest || currentPlan() || '').trim().toUpperCase();
    const actionName = String(extra.action_name || '').trim().toLowerCase();
    const dedupeKey = `${PAGE_SEEN_PREFIX}${eventName}:${window.location.pathname}:${ticker}:${plan}`;

    if (options.oncePerPage) {
      try {
        if (sessionStorage.getItem(dedupeKey) === '1') return;
        sessionStorage.setItem(dedupeKey, '1');
      } catch (_) {}
    }

    const payload = {
      event_name: eventName,
      action_name: actionName || null,
      source_path: String(window.location.pathname || '/').slice(0, 256),
      ticker: /^[A-Z0-9]{3}$/.test(ticker) ? ticker : null,
      plan_interest: plan === 'FREE' || plan === 'PREMIUM' ? plan : null,
      session_id: anonymousSessionId(),
      ...attribution(),
    };

    fetch(endpoint(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      credentials: 'omit',
      cache: 'no-store',
      keepalive: true,
    }).catch(() => {
      // Analytics is strictly non-blocking. Product behavior must never depend on it.
    });
  }

  function withTicker(href) {
    const ticker = currentTicker();
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
      const action = el.getAttribute('data-conversion-action') || '';
      try { sessionStorage.setItem('stockradar:last_conversion_action', action); } catch (_) {}
      sendEvent('conversion_click', {
        action_name: action,
        plan_interest: /premium/i.test(action) ? 'PREMIUM' : currentPlan(),
      });
    });
  });

  document.querySelectorAll('[data-stock-search-form]').forEach((form) => {
    form.addEventListener('submit', () => {
      const ticker = String(form.elements?.ticker?.value || '').trim().toUpperCase();
      if (/^[A-Z0-9]{3}$/.test(ticker)) {
        rememberTicker(ticker);
        sendEvent('ticker_lookup_submit', { ticker });
      }
    });
  });

  document.querySelectorAll('[data-auth-signup-form]').forEach((form) => {
    form.addEventListener('submit', () => {
      sendEvent('signup_submit', { plan_interest: currentPlan() });
    });
  });

  const proposition = String(body?.dataset?.proposition || '');
  const path = window.location.pathname.replace(/\/+$/, '') || '/';

  if (path === '/' || proposition === 'organic') {
    sendEvent('home_view', {}, { oncePerPage: true });
  }
  if (proposition === 'stock-report') {
    sendEvent('stock_report_view', {}, { oncePerPage: true });
    if (document.querySelector('.premium-preview-v3')) {
      sendEvent('premium_preview_view', { plan_interest: 'PREMIUM' }, { oncePerPage: true });
    }
  }
  if (proposition === 'premium-sample') {
    sendEvent('premium_sample_view', { plan_interest: 'PREMIUM' }, { oncePerPage: true });
  }
  if (proposition === 'plans') {
    sendEvent('pricing_view', {}, { oncePerPage: true });
  }
  if (proposition === 'performance') {
    sendEvent('performance_proof_view', {}, { oncePerPage: true });
  }
  if (isSignup) {
    sendEvent('signup_view', { plan_interest: currentPlan() }, { oncePerPage: true });
    if (currentPlan() === 'PREMIUM') {
      sendEvent('signup_premium_view', { plan_interest: 'PREMIUM' }, { oncePerPage: true });
    }
  }
  if (proposition === 'checkout') {
    sendEvent('checkout_view', { plan_interest: 'PREMIUM' }, { oncePerPage: true });
  }
})();
