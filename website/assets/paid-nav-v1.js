(() => {
  'use strict';

  const config = window.STOCKRADAR_AUTH_CONFIG || {};
  const STORAGE_KEY = 'stockradar-auth';
  const runtime = { client: null, user: null, tier: 'GUEST', observer: null, renderQueued: false };

  function siteUrl(path = '') {
    return new URL(String(path).replace(/^\/+/, ''), document.baseURI).toString();
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[character]));
  }

  function aiStorageKey() {
    try {
      const ref = new URL(String(config.supabaseUrl || '')).hostname.split('.')[0];
      return ref ? `sb-${ref}-auth-token` : '';
    } catch (_) {
      return '';
    }
  }

  // ai-assistant.js historically used Supabase's default storage key while the
  // rest of StockRadar uses `stockradar-auth`. Keep both stores synchronized so
  // one browser session is seen consistently by the header and StockRadar AI.
  function syncAiAuthStorageFromPrimary() {
    const secondary = aiStorageKey();
    if (!secondary || secondary === STORAGE_KEY) return;
    try {
      const primaryValue = localStorage.getItem(STORAGE_KEY);
      if (primaryValue) {
        if (localStorage.getItem(secondary) !== primaryValue) localStorage.setItem(secondary, primaryValue);
      } else {
        localStorage.removeItem(secondary);
      }
    } catch (_) {}
  }

  syncAiAuthStorageFromPrimary();

  function loadSupabaseLibrary() {
    if (window.supabase?.createClient) return Promise.resolve();
    if (window.__stockradarSupabaseLoading) return window.__stockradarSupabaseLoading;
    window.__stockradarSupabaseLoading = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2';
      script.async = true;
      script.onload = resolve;
      script.onerror = () => reject(new Error('Supabase unavailable'));
      document.head.append(script);
    });
    return window.__stockradarSupabaseLoading;
  }

  async function getClient() {
    if (runtime.client) return runtime.client;
    if (!config.configured || !config.supabaseUrl || !config.supabasePublishableKey) return null;
    await loadSupabaseLibrary();
    if (window.StockRadarAuthClient) {
      runtime.client = window.StockRadarAuthClient;
      return runtime.client;
    }
    runtime.client = window.supabase.createClient(config.supabaseUrl, config.supabasePublishableKey, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, storageKey: STORAGE_KEY },
    });
    window.StockRadarAuthClient = runtime.client;
    return runtime.client;
  }

  function premiumTier(value) {
    const tier = String(value || '').trim().toUpperCase();
    // TRIAL is accepted only as a legacy backend value. User-facing StockRadar
    // has exactly three states: Guest -> Free -> Premium.
    return tier === 'PAID' || tier === 'TRIAL';
  }

  function renderNav(nav, signedIn, premium) {
    const links = signedIn ? [
      ['./', 'AI StockRadar'],
      ['hom-nay/', 'Hôm nay'],
      ['tai-khoan/', 'My StockRadar'],
      ['radar5/', 'Radar'],
      ['hieu-qua/', 'Hiệu quả'],
    ] : [
      ['./', 'AI StockRadar'],
      ['hom-nay/', 'Hôm nay'],
      ['kiem-tra-co-phieu/', 'Tra cứu mã'],
      ['radar5/', 'Radar'],
      ['hieu-qua/', 'Hiệu quả'],
    ];

    const currentPath = location.pathname.replace(/\/+$/, '') + '/';
    nav.replaceChildren(...links.map(([path, label]) => {
      const a = document.createElement('a');
      a.href = siteUrl(path);
      a.textContent = label;
      if (premium && label === 'My StockRadar') a.dataset.premiumNav = '1';
      try {
        const targetPath = new URL(a.href).pathname.replace(/\/+$/, '') + '/';
        if (targetPath === currentPath) a.setAttribute('aria-current', 'page');
      } catch (_) {}
      return a;
    }));
  }

  function guestHeader(group) {
    group.dataset.accountState = 'guest';
    group.innerHTML = `<a class="header-login-cta" href="${siteUrl('dang-nhap/')}">Đăng nhập</a><a class="header-register-cta" href="${siteUrl('dang-ky/?plan=free')}">Đăng ký miễn phí</a>`;
  }

  function signedInHeader(group, user, premium) {
    const email = escapeHtml(user?.email || 'Tài khoản');
    const initial = escapeHtml((user?.email || 'S').slice(0, 1).toUpperCase());
    group.dataset.accountState = premium ? 'premium' : 'free';
    group.innerHTML = `<a class="auth-account-link" href="${siteUrl('tai-khoan/')}" title="${email}"><span class="auth-avatar">${initial}</span><span class="auth-account-email">${email}</span></a>${premium ? '<span class="header-account-tier">Premium</span>' : `<a class="header-register-cta" href="${siteUrl('thanh-toan/?plan=premium')}">Nâng Premium</a>`}<button class="auth-logout" type="button" data-global-auth-logout>Đăng xuất</button>`;
  }

  function canonicalizeHeader() {
    const header = document.querySelector('.site-header');
    if (!header) return;
    const group = header.querySelector('[data-header-auth-actions]');
    if (!group) return;

    // Remove the older auth.js header block when both runtimes are present.
    header.querySelectorAll('[data-auth-nav]').forEach(node => node.remove());
    group.hidden = false;
    group.removeAttribute('aria-hidden');

    if (runtime.user) signedInHeader(group, runtime.user, premiumTier(runtime.tier));
    else guestHeader(group);
  }

  async function resolveAccount() {
    const client = await getClient();
    if (!client) {
      runtime.user = null;
      runtime.tier = 'GUEST';
      return;
    }

    const { data: userData } = await client.auth.getUser();
    runtime.user = userData?.user || null;
    if (!runtime.user) {
      runtime.tier = 'GUEST';
      return;
    }

    runtime.tier = 'FREE';
    const { data: profile, error } = await client
      .from('profiles')
      .select('account_tier,account_status')
      .eq('id', runtime.user.id)
      .maybeSingle();
    if (!error && String(profile?.account_status || '').toUpperCase() === 'ACTIVE') {
      runtime.tier = premiumTier(profile?.account_tier) ? 'PAID' : 'FREE';
    }
  }

  async function renderAll() {
    const nav = document.querySelector('[data-nav-menu]');
    await resolveAccount();
    syncAiAuthStorageFromPrimary();
    canonicalizeHeader();
    if (nav) renderNav(nav, Boolean(runtime.user), premiumTier(runtime.tier));
  }

  function wireHeaderActions() {
    const header = document.querySelector('.site-header');
    if (!header || header.dataset.stockradarAuthWired === '1') return;
    header.dataset.stockradarAuthWired = '1';
    header.addEventListener('click', async event => {
      const logout = event.target.closest('[data-global-auth-logout]');
      if (!logout) return;
      const client = await getClient();
      logout.disabled = true;
      try { if (client) await client.auth.signOut(); } catch (_) {}
      try {
        localStorage.removeItem(STORAGE_KEY);
        const secondary = aiStorageKey();
        if (secondary) localStorage.removeItem(secondary);
      } catch (_) {}
      location.href = siteUrl('./');
    });
  }

  function observeHeader() {
    const header = document.querySelector('.site-header');
    if (!header || runtime.observer) return;
    runtime.observer = new MutationObserver(() => {
      if (runtime.renderQueued) return;
      runtime.renderQueued = true;
      requestAnimationFrame(() => {
        runtime.renderQueued = false;
        canonicalizeHeader();
      });
    });
    runtime.observer.observe(header, { childList: true, subtree: true });
  }

  async function mount() {
    wireHeaderActions();
    observeHeader();
    await renderAll();
    const client = await getClient();
    client?.auth?.onAuthStateChange?.(() => {
      syncAiAuthStorageFromPrimary();
      setTimeout(renderAll, 0);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
