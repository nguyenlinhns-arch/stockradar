(() => {
  'use strict';

  const config = window.STOCKRADAR_AUTH_CONFIG || {};
  const STORAGE_KEY = 'stockradar-auth';

  function likelySignedIn() {
    try { return Boolean(localStorage.getItem(STORAGE_KEY)); } catch (_) { return false; }
  }

  function siteUrl(path = '') {
    return new URL(String(path).replace(/^\/+/, ''), document.baseURI).toString();
  }

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
    if (!config.configured || !config.supabaseUrl || !config.supabasePublishableKey) return null;
    await loadSupabaseLibrary();
    if (window.StockRadarAuthClient) return window.StockRadarAuthClient;
    window.StockRadarAuthClient = window.supabase.createClient(config.supabaseUrl, config.supabasePublishableKey, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, storageKey: STORAGE_KEY },
    });
    return window.StockRadarAuthClient;
  }

  function renderNav(nav, premium) {
    const links = premium ? [
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
      try {
        const targetPath = new URL(a.href).pathname.replace(/\/+$/, '') + '/';
        if (targetPath === currentPath) a.setAttribute('aria-current', 'page');
      } catch (_) {}
      return a;
    }));
  }

  async function mount() {
    const nav = document.querySelector('[data-nav-menu]');
    if (!nav || !likelySignedIn()) return;

    try {
      const client = await getClient();
      if (!client) return;
      const { data: userData, error: userError } = await client.auth.getUser();
      const user = userData?.user;
      if (userError || !user) return;

      const { data: profile, error: profileError } = await client
        .from('profiles')
        .select('account_tier,account_status')
        .eq('id', user.id)
        .maybeSingle();
      if (profileError) return;

      const tier = String(profile?.account_tier || 'FREE').toUpperCase();
      const active = String(profile?.account_status || '').toUpperCase() === 'ACTIVE';
      renderNav(nav, active && (tier === 'PAID' || tier === 'TRIAL'));
    } catch (_) {
      // Public navigation remains intact if account state cannot be resolved.
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
