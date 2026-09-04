(() => {
  'use strict';

  const REFRESH_MS = 60_000;
  const ACCOUNT_ALERTS_URL = 'tai-khoan/#stockradar-notification-title';
  let refreshTimer = 0;
  let client = null;
  let bell = null;
  let badge = null;
  let refreshInFlight = false;

  function siteUrl(path = '') {
    return new URL(String(path).replace(/^\/+/, ''), document.baseURI).toString();
  }

  function getClient() {
    if (window.StockRadarAuthClient) return window.StockRadarAuthClient;
    const config = window.STOCKRADAR_AUTH_CONFIG || {};
    if (!window.supabase?.createClient || !config.configured) return null;
    window.StockRadarAuthClient = window.supabase.createClient(
      config.supabaseUrl,
      config.supabasePublishableKey,
      {
        auth: {
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true,
          storageKey: 'stockradar-auth',
        },
      },
    );
    return window.StockRadarAuthClient;
  }

  function ensureBell() {
    if (bell?.isConnected) return bell;
    const nav = document.querySelector('.site-header .nav');
    if (!nav) return null;

    bell = document.createElement('a');
    bell.className = 'header-notification-bell';
    bell.href = siteUrl(ACCOUNT_ALERTS_URL);
    bell.hidden = true;
    bell.setAttribute('aria-label', 'Thông báo StockRadar');
    bell.setAttribute('title', 'Thông báo StockRadar');
    bell.innerHTML = `
      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" />
      </svg>
      <span class="header-notification-badge" data-header-notification-badge hidden>0</span>`;
    badge = bell.querySelector('[data-header-notification-badge]');

    const menu = nav.querySelector('[data-nav-menu]');
    if (menu) menu.after(bell);
    else nav.append(bell);
    return bell;
  }

  function setCount(count) {
    if (!bell) return;
    const safeCount = Math.max(0, Number(count) || 0);
    const display = safeCount > 99 ? '99+' : String(safeCount);
    if (badge) {
      badge.textContent = display;
      badge.hidden = safeCount < 1;
    }
    bell.setAttribute(
      'aria-label',
      safeCount > 0 ? `Thông báo StockRadar, ${safeCount} chưa đọc` : 'Thông báo StockRadar, không có thông báo chưa đọc',
    );
    bell.setAttribute(
      'title',
      safeCount > 0 ? `${safeCount} cảnh báo chưa đọc` : 'Thông báo StockRadar',
    );
  }

  function hideBell() {
    if (!bell) return;
    bell.hidden = true;
    setCount(0);
  }

  async function unreadCount() {
    const now = new Date().toISOString();
    const { count, error } = await client
      .from('stockradar_notifications')
      .select('id', { count: 'exact', head: true })
      .is('read_at', null)
      .gt('expires_at', now);
    if (error) throw error;
    return Number(count || 0);
  }

  async function refresh({ quiet = true } = {}) {
    if (!client || refreshInFlight) return;
    refreshInFlight = true;
    try {
      const { data, error } = await client.auth.getSession();
      if (error || !data?.session?.user) {
        hideBell();
        return;
      }
      const target = ensureBell();
      if (!target) return;
      target.hidden = false;
      setCount(await unreadCount());
    } catch (error) {
      if (!quiet) console.error('StockRadar header notification refresh failed', error);
      hideBell();
    } finally {
      refreshInFlight = false;
    }
  }

  async function mount() {
    client = getClient();
    if (!client) return;
    ensureBell();
    await refresh({ quiet: true });

    client.auth.onAuthStateChange((_event, session) => {
      if (!session?.user) {
        hideBell();
        return;
      }
      window.setTimeout(() => refresh({ quiet: true }), 0);
    });

    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') refresh({ quiet: true });
    });

    window.clearInterval(refreshTimer);
    refreshTimer = window.setInterval(() => {
      if (document.visibilityState === 'visible') refresh({ quiet: true });
    }, REFRESH_MS);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount, { once: true });
  } else {
    mount();
  }
})();
