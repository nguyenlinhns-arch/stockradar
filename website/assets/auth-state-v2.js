(() => {
  'use strict';
  if (window.__stockradarAuthStateMounted) return;
  window.__stockradarAuthStateMounted = true;

  const config = window.STOCKRADAR_AUTH_CONFIG || {};
  const STORAGE_KEY = 'stockradar-auth';
  const STYLE_ID = 'stockradar-auth-state-style-v3';
  const state = {
    client: null,
    user: null,
    premium: false,
    observer: null,
    scheduled: false,
    copyObserver: null,
    copyScheduled: false,
  };

  function siteUrl(path = '') {
    return new URL(String(path).replace(/^\/+/, ''), document.baseURI).toString();
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  function defaultSupabaseStorageKey() {
    try {
      const projectRef = new URL(String(config.supabaseUrl || '')).hostname.split('.')[0];
      return projectRef ? `sb-${projectRef}-auth-token` : '';
    } catch (_) {
      return '';
    }
  }

  function bridgeSessionStorage() {
    const secondary = defaultSupabaseStorageKey();
    if (!secondary || secondary === STORAGE_KEY) return;
    try {
      const migrated = 'stockradar-auth-migrated-v1';
      if (localStorage.getItem(migrated)) return;
      const primaryValue = localStorage.getItem(STORAGE_KEY);
      const secondaryValue = localStorage.getItem(secondary);
      if (primaryValue) {
        // Keep the current session. Never mirror a token that can resurrect logout.
      } else if (secondaryValue) {
        localStorage.setItem(STORAGE_KEY, secondaryValue);
      }
      localStorage.removeItem(secondary);
      localStorage.setItem(migrated, '1');
    } catch (_) {}
  }

  bridgeSessionStorage();

  function loadSupabase() {
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

  async function client() {
    if (state.client) return state.client;
    if (!config.configured || !config.supabaseUrl || !config.supabasePublishableKey) return null;
    await loadSupabase();
    if (window.StockRadarAuthClient) {
      state.client = window.StockRadarAuthClient;
      return state.client;
    }
    state.client = window.supabase.createClient(config.supabaseUrl, config.supabasePublishableKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
        storageKey: STORAGE_KEY,
        storage: window.localStorage,
      },
    });
    window.StockRadarAuthClient = state.client;
    return state.client;
  }

  function isPremiumTier(value) {
    const tier = String(value || '').toUpperCase();
    // TRIAL is retained only as a legacy backend compatibility value. The UI
    // intentionally exposes only Guest -> Free -> Premium.
    return tier === 'PAID' || tier === 'TRIAL';
  }

  async function resolveState() {
    const auth = await client();
    if (!auth) {
      state.user = null;
      state.premium = false;
      return;
    }

    let session = null;
    try {
      const { data } = await auth.auth.getSession();
      session = data?.session || null;
    } catch (_) {}

    state.user = session?.user || null;
    if (!state.user) {
      try {
        const { data } = await auth.auth.getUser();
        state.user = data?.user || null;
      } catch (_) {
        state.user = null;
      }
    }

    state.premium = false;
    if (!state.user) return;

    try {
      const { data: profile, error } = await auth.rpc('get_my_stockradar_access');
      if (error) return;
      const active = String(profile?.account_status || '').toUpperCase() === 'ACTIVE';
      state.premium = active && isPremiumTier(profile?.account_tier);
    } catch (_) {}
  }

  function desiredHeaderHtml() {
    if (!state.user) {
      return `<a class="header-login-cta" href="${siteUrl('dang-nhap/')}">Đăng nhập</a><a class="header-register-cta" href="${siteUrl('dang-ky/?plan=free')}">Đăng ký miễn phí</a>`;
    }
    const email = escapeHtml(state.user.email || 'Tài khoản');
    const initial = escapeHtml((state.user.email || 'S').slice(0, 1).toUpperCase());
    return `<a class="auth-account-link" href="${siteUrl('tai-khoan/')}" title="${email}"><span class="auth-avatar">${initial}</span><span class="auth-account-email">${email}</span></a>${state.premium ? '<span class="header-account-tier">Premium</span>' : `<a class="button button-primary button-small header-account-upgrade" href="${siteUrl('thanh-toan/?plan=premium')}">Nâng Premium</a>`}<button class="auth-logout" type="button" data-auth-state-logout>Đăng xuất</button>`;
  }

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      [data-header-auth-actions]{display:flex;align-items:center;gap:8px;margin-left:auto;flex:0 0 auto;min-width:0}
      [data-header-auth-actions] .header-login-cta,[data-header-auth-actions] .header-register-cta,[data-header-auth-actions] .auth-logout{min-height:36px;display:inline-flex;align-items:center;justify-content:center;border-radius:8px;font-size:12px;font-weight:800;white-space:nowrap}
      [data-header-auth-actions] .header-login-cta{padding:0 7px;color:#24415d}
      [data-header-auth-actions] .header-register-cta{padding:0 11px;background:#0d2b49;color:#fff}
      [data-header-auth-actions] .auth-account-link{display:flex;align-items:center;gap:7px;min-width:0;max-width:190px;color:#24384c;font-size:12px;font-weight:800}
      [data-header-auth-actions] .auth-avatar{width:30px;height:30px;display:inline-flex;align-items:center;justify-content:center;border-radius:50%;background:#0d2b49;color:#fff;font-size:12px;font-weight:900;flex:0 0 auto}
      [data-header-auth-actions] .auth-account-email{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
      [data-header-auth-actions] .header-account-tier{display:inline-flex;align-items:center;min-height:26px;padding:0 8px;border-radius:999px;background:#e8f6f1;color:#08724f;font-size:10px;font-weight:900;text-transform:uppercase}
      [data-header-auth-actions] .header-account-upgrade{min-height:34px;padding:0 10px;font-size:11px}
      [data-header-auth-actions] .auth-logout{border:0;background:transparent;color:#65758a;padding:0 4px;cursor:pointer}
      [data-header-auth-actions] .auth-logout:hover,[data-header-auth-actions] .header-login-cta:hover{color:#cf2430}
      @media(max-width:900px){[data-header-auth-actions] .auth-account-email,[data-header-auth-actions] .header-account-tier{display:none}[data-header-auth-actions] .auth-account-link{max-width:none}}
      @media(max-width:720px){[data-header-auth-actions] .header-register-cta,[data-header-auth-actions] .header-account-upgrade,[data-header-auth-actions] .auth-logout{display:none}[data-header-auth-actions]{gap:4px}[data-header-auth-actions] .header-login-cta{padding:0 4px;font-size:11px}[data-header-auth-actions] .auth-avatar{width:28px;height:28px}}
    `;
    document.head.append(style);
  }

  function ensureHeaderGroup(header) {
    let group = header.querySelector('[data-header-auth-actions]');
    if (group) return group;
    const nav = header.querySelector('.nav') || header;
    group = document.createElement('div');
    group.className = 'header-auth-actions';
    group.dataset.headerAuthActions = '';
    group.setAttribute('aria-label', 'Tài khoản StockRadar');
    nav.append(group);
    return group;
  }

  function renderHeader() {
    const header = document.querySelector('.site-header');
    if (!header) return;
    ensureStyles();
    const group = ensureHeaderGroup(header);

    header.querySelectorAll('[data-auth-nav]').forEach(node => node.remove());
    group.hidden = false;
    group.removeAttribute('aria-hidden');
    group.dataset.accountState = state.user ? (state.premium ? 'premium' : 'free') : 'guest';

    const html = desiredHeaderHtml();
    const template = document.createElement('template');
    template.innerHTML = html;
    if (group.innerHTML !== template.innerHTML) group.replaceChildren(template.content.cloneNode(true));
  }

  function normalizeText(value) {
    return String(value || '')
      .replace(/Trial\s*\/\s*Paid/gi, 'Premium')
      .replace(/Trial\s*\/\s*Premium/gi, 'Premium')
      .replace(/\bTRIAL\b/g, 'Premium')
      .replace(/\bTrial\b/g, 'Premium')
      .replace(/\bPAID\b/g, 'Premium')
      .replace(/\bPaid\b/g, 'Premium');
  }

  function normalizeTextNodes(target) {
    if (!target) return;
    const walker = document.createTreeWalker(target, NodeFilter.SHOW_TEXT);
    const nodes = [];
    let current = walker.nextNode();
    while (current) {
      nodes.push(current);
      current = walker.nextNode();
    }
    nodes.forEach(textNode => {
      const before = String(textNode.nodeValue || '');
      const after = normalizeText(before);
      if (after !== before) textNode.nodeValue = after;
    });
  }

  function normalizeVisibleTierCopy() {
    document.querySelectorAll(
      '.sr-center-plan,.sr-center-meta,.sr-center-foot,[data-account-tier],[data-email-pref-tier],[data-email-health-tier],[data-product-email-tier-note],[data-email-health-note],.auth-security-note'
    ).forEach(normalizeTextNodes);
  }

  function observeHeader() {
    const header = document.querySelector('.site-header');
    if (!header || state.observer) return;
    state.observer = new MutationObserver(() => {
      if (state.scheduled) return;
      state.scheduled = true;
      requestAnimationFrame(() => {
        state.scheduled = false;
        renderHeader();
      });
    });
    state.observer.observe(header, { childList: true, subtree: true, attributes: true, attributeFilter: ['hidden', 'href', 'class'] });
  }

  function observeTierCopy() {
    if (!document.body || state.copyObserver) return;
    state.copyObserver = new MutationObserver(() => {
      if (state.copyScheduled) return;
      state.copyScheduled = true;
      requestAnimationFrame(() => {
        state.copyScheduled = false;
        normalizeVisibleTierCopy();
      });
    });
    state.copyObserver.observe(document.body, { childList: true, subtree: true, characterData: true });
  }

  async function logout() {
    const auth = await client();
    try { if (auth) await auth.auth.signOut(); } catch (_) {}
    try {
      localStorage.removeItem(STORAGE_KEY);
      const secondary = defaultSupabaseStorageKey();
      if (secondary) localStorage.removeItem(secondary);
    } catch (_) {}
    location.href = siteUrl('./');
  }

  window.addEventListener('stockradar-access-changed', () => { refresh(); });

  async function refresh() {
    bridgeSessionStorage();
    await resolveState();
    renderHeader();
    normalizeVisibleTierCopy();
    document.documentElement.dataset.stockradarAccountState = state.user ? (state.premium ? 'premium' : 'free') : 'guest';
  }

  function isDedicatedAuthSurface() {
    return Boolean(document.querySelector('[data-auth-login-form],[data-auth-signup-form],[data-auth-account]'));
  }

  async function mount() {
    if (isDedicatedAuthSurface()) return;
    window.StockRadarHeaderOwner = 'auth-state';
    observeHeader();
    observeTierCopy();
    document.addEventListener('click', event => {
      if (event.target.closest('[data-auth-state-logout]')) logout();
    });
    await refresh();
    const auth = await client();
    auth?.auth?.onAuthStateChange?.(() => {
      setTimeout(refresh, 0);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
