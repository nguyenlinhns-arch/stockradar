(() => {
  'use strict';

  const config = window.STOCKRADAR_AUTH_CONFIG || {};
  const STORAGE_KEY = 'stockradar-auth';
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
      const primary = localStorage.getItem(STORAGE_KEY);
      if (primary) {
        if (localStorage.getItem(secondary) !== primary) localStorage.setItem(secondary, primary);
      } else {
        localStorage.removeItem(secondary);
      }
    } catch (_) {}
  }

  bridgeSessionStorage();

  function loadSupabase() {
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
    const { data } = await auth.auth.getUser();
    state.user = data?.user || null;
    state.premium = false;
    if (!state.user) return;

    const { data: profile } = await auth
      .from('profiles')
      .select('account_tier,account_status')
      .eq('id', state.user.id)
      .maybeSingle();
    const active = String(profile?.account_status || '').toUpperCase() === 'ACTIVE';
    state.premium = active && isPremiumTier(profile?.account_tier);
  }

  function desiredHeaderHtml() {
    if (!state.user) {
      return `<a class="header-login-cta" href="${siteUrl('dang-nhap/')}">Đăng nhập</a><a class="header-register-cta" href="${siteUrl('dang-ky/?plan=free')}">Đăng ký miễn phí</a>`;
    }
    const email = escapeHtml(state.user.email || 'Tài khoản');
    const initial = escapeHtml((state.user.email || 'S').slice(0, 1).toUpperCase());
    return `<a class="auth-account-link" href="${siteUrl('tai-khoan/')}" title="${email}"><span class="auth-avatar">${initial}</span><span class="auth-account-email">${email}</span></a>${state.premium ? '<span class="header-account-tier">Premium</span>' : `<a class="button button-primary button-small header-account-upgrade" href="${siteUrl('thanh-toan/?plan=premium')}">Nâng Premium</a>`}<button class="auth-logout" type="button" data-auth-state-logout>Đăng xuất</button>`;
  }

  function renderHeader() {
    const header = document.querySelector('.site-header');
    if (!header) return;
    const group = header.querySelector('[data-header-auth-actions]');
    if (!group) return;

    header.querySelectorAll('[data-auth-nav]').forEach(node => node.remove());
    group.hidden = false;
    group.removeAttribute('aria-hidden');
    group.dataset.accountState = state.user ? (state.premium ? 'premium' : 'free') : 'guest';

    const html = desiredHeaderHtml();
    if (group.innerHTML !== html) group.innerHTML = html;
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

  function normalizeVisibleTierCopy() {
    document.querySelectorAll(
      '.sr-center-plan,.sr-center-meta,.sr-center-foot,[data-account-tier],[data-email-pref-tier],[data-email-health-tier],[data-product-email-tier-note],[data-email-health-note],.auth-security-note'
    ).forEach(target => {
      const before = String(target.textContent || '');
      const after = normalizeText(before);
      if (after !== before) target.textContent = after;
    });
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

  async function refresh() {
    bridgeSessionStorage();
    await resolveState();
    renderHeader();
    normalizeVisibleTierCopy();
    document.documentElement.dataset.stockradarAccountState = state.user ? (state.premium ? 'premium' : 'free') : 'guest';
  }

  async function mount() {
    observeHeader();
    observeTierCopy();
    document.addEventListener('click', event => {
      if (event.target.closest('[data-auth-state-logout]')) logout();
    });
    await refresh();
    const auth = await client();
    auth?.auth?.onAuthStateChange?.(() => {
      bridgeSessionStorage();
      setTimeout(refresh, 0);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
