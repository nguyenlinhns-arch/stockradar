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

  function syncAiAuthStorageFromPrimary() {
    const secondary = aiStorageKey();
    if (!secondary || secondary === STORAGE_KEY) return;
    try {
      const marker = 'stockradar-auth-migrated-v1';
      if (!localStorage.getItem(marker) && !localStorage.getItem(STORAGE_KEY)) {
        const legacy = localStorage.getItem(secondary);
        if (legacy) localStorage.setItem(STORAGE_KEY, legacy);
      }
      localStorage.removeItem(secondary);
      localStorage.setItem(marker, '1');
    } catch (_) {}
  }

  syncAiAuthStorageFromPrimary();

  function loadSupabaseLibrary() {
    if (window.supabase?.createClient) return Promise.resolve();
    if (window.__stockradarSupabaseLoading) return window.__stockradarSupabaseLoading;
    window.__stockradarSupabaseLoading = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.95.0';
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
    return tier === 'PAID' || tier === 'TRIAL';
  }

  function renderNav(nav, signedIn, premium) {
    const links = signedIn ? [
      ['./#stockradar-ai', 'AI'],
      ['radar5/', 'Radar'],
      ['khuyen-nghi/', 'Khuyến nghị'],
      ['hieu-qua/', 'Hiệu quả'],
      ['tai-khoan/', 'My StockRadar'],
    ] : [
      ['./#stockradar-ai', 'AI'],
      ['radar5/', 'Radar'],
      ['khuyen-nghi/', 'Khuyến nghị'],
      ['hieu-qua/', 'Hiệu quả'],
      ['dang-ky/', 'Gói'],
    ];

    const currentPath = location.pathname.replace(/\/+$/, '') + '/';
    const fragment = document.createDocumentFragment();
    links.forEach(([path, label]) => {
      const a = document.createElement('a');
      a.href = siteUrl(path);
      a.textContent = label;
      if (premium && label === 'My StockRadar') a.dataset.premiumNav = '1';
      try {
        const targetPath = new URL(a.href).pathname.replace(/\/+$/, '') + '/';
        if (targetPath === currentPath) a.setAttribute('aria-current', 'page');
      } catch (_) {}
      fragment.append(a);
    });
    nav.replaceChildren(fragment);
  }

  function desiredHeaderHtml() {
    if (!runtime.user) {
      return `<a class="header-login-cta" href="${siteUrl('dang-nhap/')}">Đăng nhập</a><a class="header-register-cta" href="${siteUrl('dang-ky/?plan=free')}">Bắt đầu miễn phí</a>`;
    }
    const email = escapeHtml(runtime.user.email || 'Tài khoản');
    const initial = escapeHtml((runtime.user.email || 'S').slice(0, 1).toUpperCase());
    const premium = premiumTier(runtime.tier);
    return `<a class="auth-account-link" href="${siteUrl('tai-khoan/')}" title="${email}"><span class="auth-avatar">${initial}</span><span class="auth-account-email">${email}</span></a>${premium ? '<span class="header-account-tier">Premium</span>' : `<a class="button button-primary button-small header-account-upgrade" href="${siteUrl('thanh-toan/?plan=premium')}">Nâng Premium</a>`}<button class="auth-logout" type="button" data-global-auth-logout>Đăng xuất</button>`;
  }

  function canonicalizeHeader() {
    if (window.StockRadarHeaderOwner === 'auth-state') return;
    const header = document.querySelector('.site-header');
    if (!header) return;
    const group = header.querySelector('[data-header-auth-actions]');
    if (!group) return;

    header.querySelectorAll('[data-auth-nav]').forEach(node => node.remove());
    group.hidden = false;
    group.removeAttribute('aria-hidden');
    group.dataset.accountState = runtime.user ? (premiumTier(runtime.tier) ? 'premium' : 'free') : 'guest';

    const html = desiredHeaderHtml();
    const template = document.createElement('template');
    template.innerHTML = html;
    if (group.innerHTML !== template.innerHTML) group.replaceChildren(template.content.cloneNode(true));
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
    const { data: profile, error } = await client.rpc('get_my_stockradar_access');
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
    runtime.observer.observe(header, { childList: true, subtree: true, attributes: true, attributeFilter: ['hidden', 'href', 'class'] });
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
