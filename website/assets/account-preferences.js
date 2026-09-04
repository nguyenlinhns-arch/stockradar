(() => {
  'use strict';

  const HORIZON_LABELS = Object.freeze({
    SHORT_TERM: 'Ngắn hạn',
    MEDIUM_TERM: 'Trung hạn',
    LONG_TERM: 'Dài hạn',
    ACCUMULATION: 'Tích sản',
  });

  function siteUrl(path = '') {
    return new URL(String(path).replace(/^\/+/, ''), document.baseURI).toString();
  }

  function getClient() {
    if (window.StockRadarAuthClient) return window.StockRadarAuthClient;
    const config = window.STOCKRADAR_AUTH_CONFIG || {};
    if (!window.supabase?.createClient || !config.configured) return null;
    window.StockRadarAuthClient = window.supabase.createClient(config.supabaseUrl, config.supabasePublishableKey, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, storageKey: 'stockradar-auth' },
    });
    return window.StockRadarAuthClient;
  }

  function setMessage(target, message, kind = '') {
    if (!target) return;
    target.className = `auth-message${kind ? ` ${kind}` : ''}`;
    target.textContent = message;
  }

  function normalizeTicker(value) {
    return String(value || '').trim().toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 3);
  }

  function selectedValues(form, name) {
    return Array.from(form.querySelectorAll(`input[name="${name}"]:checked`)).map(input => input.value);
  }

  function friendlyDatabaseError(error) {
    const raw = String(error?.message || '').toLowerCase();
    if (raw.includes('watchlist limit reached')) return 'Đã đạt giới hạn danh sách theo dõi của gói hiện tại.';
    if (raw.includes('verified active stockradar account required')) return 'Cần xác minh email trước khi lưu danh sách theo dõi.';
    if (raw.includes('duplicate key')) return 'Mã này đã có trong danh sách theo dõi.';
    if (raw.includes('row-level security') || raw.includes('permission')) return 'Phiên đăng nhập không còn quyền ghi dữ liệu. Hãy đăng nhập lại.';
    return 'Chưa thể lưu dữ liệu. Vui lòng thử lại.';
  }

  function enforceSectorLimit(form) {
    const boxes = Array.from(form.querySelectorAll('input[name="preferred_sectors"]'));
    const checked = boxes.filter(box => box.checked);
    boxes.forEach(box => { box.disabled = !box.checked && checked.length >= 3; });
  }

  function renderWatchlist(target, items) {
    if (!target) return;
    if (!items.length) {
      target.innerHTML = '<div class="account-empty-state">Chưa có mã theo dõi. Thêm tối đa theo giới hạn gói của bạn.</div>';
      return;
    }
    target.innerHTML = items.map(item => {
      const ticker = String(item.ticker || '').replace(/[^A-Z0-9]/g, '');
      const horizon = HORIZON_LABELS[item.horizon] || item.horizon || '—';
      return `<article class="watchlist-row" data-watchlist-id="${item.id}">
        <div class="watchlist-main"><a href="${siteUrl(`co-phieu/${ticker}/`)}"><strong>${ticker}</strong></a><span>${horizon}${item.owns_stock ? ' · Đang sở hữu' : ''}</span></div>
        <button class="button button-secondary button-small" type="button" data-watchlist-remove>Gỡ</button>
      </article>`;
    }).join('');
  }

  async function loadProfile(client, userId) {
    const { data, error } = await client
      .from('profiles')
      .select('account_tier,account_status')
      .eq('id', userId)
      .maybeSingle();
    if (error) throw error;
    return data || { account_tier: 'FREE', account_status: 'PENDING' };
  }

  async function loadPreferences(client, userId) {
    const { data, error } = await client
      .from('user_preferences')
      .select('preferred_horizons,preferred_sectors,updated_at')
      .eq('user_id', userId)
      .maybeSingle();
    if (error) throw error;
    return data || { preferred_horizons: [], preferred_sectors: [] };
  }

  async function loadWatchlist(client, userId) {
    const { data, error } = await client
      .from('watchlist_items')
      .select('id,ticker,horizon,owns_stock,alert_enabled,created_at')
      .eq('user_id', userId)
      .is('removed_at', null)
      .order('created_at', { ascending: true });
    if (error) throw error;
    return data || [];
  }

  async function mountAccountPreferences() {
    const root = document.querySelector('[data-account-personalization]');
    if (!root) return;

    const client = getClient();
    const status = root.querySelector('[data-personalization-status]');
    if (!client) {
      setMessage(status, 'Dịch vụ lưu tùy chọn chưa sẵn sàng.', 'error');
      return;
    }

    const { data: userData, error: userError } = await client.auth.getUser();
    const user = userData?.user;
    if (userError || !user) {
      setMessage(status, 'Đăng nhập để lưu tùy chọn và danh sách theo dõi.', 'error');
      return;
    }

    const preferencesForm = root.querySelector('[data-account-preferences-form]');
    const watchlistForm = root.querySelector('[data-account-watchlist-form]');
    const watchlistTarget = root.querySelector('[data-account-watchlist]');
    const watchlistMessage = root.querySelector('[data-watchlist-message]');
    const limitTarget = root.querySelector('[data-watchlist-limit]');
    const tickerInput = watchlistForm?.elements?.ticker;

    let profile;
    let watchlist = [];
    try {
      [profile, watchlist] = await Promise.all([
        loadProfile(client, user.id),
        loadWatchlist(client, user.id),
      ]);
      const preferences = await loadPreferences(client, user.id);
      const horizons = new Set(preferences.preferred_horizons || []);
      const sectors = new Set(preferences.preferred_sectors || []);
      preferencesForm?.querySelectorAll('input[name="preferred_horizons"]').forEach(input => { input.checked = horizons.has(input.value); });
      preferencesForm?.querySelectorAll('input[name="preferred_sectors"]').forEach(input => { input.checked = sectors.has(input.value); });
      if (preferencesForm) enforceSectorLimit(preferencesForm);
      renderWatchlist(watchlistTarget, watchlist);
      const limit = profile.account_tier === 'PAID' ? 20 : 3;
      if (limitTarget) limitTarget.textContent = `${watchlist.length}/${limit} mã`;
      setMessage(status, 'Tùy chọn được lưu theo tài khoản và bảo vệ bằng RLS.', 'success');
    } catch (error) {
      setMessage(status, friendlyDatabaseError(error), 'error');
      return;
    }

    preferencesForm?.querySelectorAll('input[name="preferred_sectors"]').forEach(input => {
      input.addEventListener('change', () => enforceSectorLimit(preferencesForm));
    });

    preferencesForm?.addEventListener('submit', async event => {
      event.preventDefault();
      const message = preferencesForm.querySelector('[data-auth-message]');
      const button = preferencesForm.querySelector('button[type="submit"]');
      const preferred_horizons = selectedValues(preferencesForm, 'preferred_horizons');
      const preferred_sectors = selectedValues(preferencesForm, 'preferred_sectors');
      if (preferred_sectors.length > 3) return setMessage(message, 'Chọn tối đa 3 ngành.', 'error');
      if (button) button.disabled = true;
      setMessage(message, 'Đang lưu…');
      try {
        const { error } = await client.from('user_preferences').upsert({
          user_id: user.id,
          preferred_horizons,
          preferred_sectors,
        }, { onConflict: 'user_id' });
        if (error) throw error;
        setMessage(message, 'Đã lưu ưu tiên phân tích.', 'success');
      } catch (error) {
        setMessage(message, friendlyDatabaseError(error), 'error');
      } finally {
        if (button) button.disabled = false;
      }
    });

    if (tickerInput) {
      tickerInput.addEventListener('input', () => { tickerInput.value = normalizeTicker(tickerInput.value); });
    }

    watchlistForm?.addEventListener('submit', async event => {
      event.preventDefault();
      const ticker = normalizeTicker(watchlistForm.elements.ticker?.value);
      const horizon = String(watchlistForm.elements.horizon?.value || 'SHORT_TERM');
      const owns_stock = Boolean(watchlistForm.elements.owns_stock?.checked);
      const button = watchlistForm.querySelector('button[type="submit"]');
      if (!/^(?=.*[A-Z])[A-Z0-9]{3}$/.test(ticker)) return setMessage(watchlistMessage, 'Nhập mã HOSE gồm đúng 3 ký tự chữ/số.', 'error');
      if (profile.account_status !== 'ACTIVE') return setMessage(watchlistMessage, 'Cần xác minh email trước khi thêm mã.', 'error');
      if (button) button.disabled = true;
      setMessage(watchlistMessage, 'Đang lưu…');
      try {
        const existing = watchlist.find(item => item.ticker === ticker && item.horizon === horizon);
        if (existing) {
          const { error } = await client
            .from('watchlist_items')
            .update({ owns_stock })
            .eq('id', existing.id)
            .eq('user_id', user.id);
          if (error) throw error;
        } else {
          const { error } = await client.from('watchlist_items').insert({
            user_id: user.id,
            ticker,
            horizon,
            owns_stock,
            alert_enabled: false,
          });
          if (error) throw error;
        }
        watchlist = await loadWatchlist(client, user.id);
        renderWatchlist(watchlistTarget, watchlist);
        const limit = profile.account_tier === 'PAID' ? 20 : 3;
        if (limitTarget) limitTarget.textContent = `${watchlist.length}/${limit} mã`;
        watchlistForm.reset();
        setMessage(watchlistMessage, existing ? 'Đã cập nhật mã theo dõi.' : 'Đã thêm mã theo dõi.', 'success');
      } catch (error) {
        setMessage(watchlistMessage, friendlyDatabaseError(error), 'error');
      } finally {
        if (button) button.disabled = false;
      }
    });

    watchlistTarget?.addEventListener('click', async event => {
      const button = event.target.closest('[data-watchlist-remove]');
      if (!button) return;
      const row = button.closest('[data-watchlist-id]');
      const id = row?.dataset.watchlistId;
      if (!id) return;
      button.disabled = true;
      try {
        const { error } = await client
          .from('watchlist_items')
          .update({ removed_at: new Date().toISOString(), alert_enabled: false })
          .eq('id', id)
          .eq('user_id', user.id);
        if (error) throw error;
        watchlist = watchlist.filter(item => item.id !== id);
        renderWatchlist(watchlistTarget, watchlist);
        const limit = profile.account_tier === 'PAID' ? 20 : 3;
        if (limitTarget) limitTarget.textContent = `${watchlist.length}/${limit} mã`;
        setMessage(watchlistMessage, 'Đã gỡ khỏi danh sách theo dõi.', 'success');
      } catch (error) {
        button.disabled = false;
        setMessage(watchlistMessage, friendlyDatabaseError(error), 'error');
      }
    });
  }

  document.addEventListener('DOMContentLoaded', mountAccountPreferences);
})();
