(() => {
  'use strict';

  const PREMIUM_TIERS = new Set(['TRIAL', 'PAID']);
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

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[character]));
  }

  function normalizeTicker(value) {
    return String(value || '').trim().toUpperCase().replace(/[^A-Z]/g, '').slice(0, 3);
  }

  function formatSnapshot(value) {
    if (!value) return 'Chưa có';
    try {
      return new Intl.DateTimeFormat('vi-VN', {
        day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false,
      }).format(new Date(value));
    } catch (_) {
      return 'Chưa có';
    }
  }

  function isBlocked(payload) {
    const status = String(payload?.data_status || payload?.status || '').toUpperCase();
    return !payload || !status || status.startsWith('BLOCKED');
  }

  async function loadJson(path) {
    try {
      const response = await fetch(siteUrl(path), { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (_) {
      return null;
    }
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
      .order('owns_stock', { ascending: false })
      .order('created_at', { ascending: true });
    if (error) throw error;
    return data || [];
  }

  async function loadEmailHealth(client) {
    try {
      const { data, error } = await client.rpc('get_my_stockradar_email_health_v1');
      if (error) throw error;
      return data || null;
    } catch (_) {
      return null;
    }
  }

  function setText(root, selector, text) {
    const target = root.querySelector(selector);
    if (target) target.textContent = text;
  }

  function renderPlan(root, profile, watchlist, health) {
    const tier = String(profile.account_tier || 'FREE').toUpperCase();
    const premium = PREMIUM_TIERS.has(tier);
    const active = String(profile.account_status || '').toUpperCase() === 'ACTIVE';
    const alertCount = watchlist.filter(item => item.alert_enabled).length;
    setText(root, '[data-paid-tier]', tier);
    setText(root, '[data-paid-watchlist-count]', `${watchlist.length}`);
    setText(root, '[data-paid-owned-count]', `${watchlist.filter(item => item.owns_stock).length}`);
    setText(root, '[data-paid-alert-count]', `${alertCount}`);
    setText(root, '[data-paid-email-state]', health?.delivery_system_ready ? 'Sẵn sàng' : health ? 'Đang kiểm tra' : 'Chưa xác định');

    const badge = root.querySelector('[data-paid-tier-badge]');
    if (badge) badge.textContent = `${tier}${active ? ' · ACTIVE' : ''}`;

    const banner = root.querySelector('[data-paid-plan-banner]');
    if (!banner) return;
    if (premium && active) {
      banner.innerHTML = `<strong>Premium đang hoạt động.</strong><span>Ưu tiên mã đang sở hữu, mã theo dõi và Action Alert đã bật. Hệ thống chỉ phát hành hành động khi dữ liệu vượt đủ gate.</span><a class="button button-secondary button-small" href="${siteUrl('tai-khoan/')}">Cài đặt cảnh báo</a>`;
    } else if (!active) {
      banner.innerHTML = `<strong>Tài khoản chưa ACTIVE.</strong><span>Xác minh email để các tùy chọn cá nhân hóa và quyền gửi email có hiệu lực.</span><a class="button button-primary button-small" href="${siteUrl('tai-khoan/')}">Kiểm tra tài khoản</a>`;
    } else {
      banner.innerHTML = `<strong>Bạn đang dùng Free.</strong><span>Bảng Hôm nay vẫn tổng hợp watchlist; Action Alert theo từng mã và nội dung hành động chuyên sâu dành cho Trial/Premium.</span><a class="button button-primary button-small" href="${siteUrl('dang-ky/')}">Xem Premium</a>`;
    }
  }

  function stockRow(item) {
    const ticker = normalizeTicker(item.ticker);
    const horizon = HORIZON_LABELS[item.horizon] || item.horizon || '—';
    return `<a class="paid-stock-row" href="${siteUrl(`co-phieu/${ticker}/`)}">
      <span class="paid-stock-ticker">${escapeHtml(ticker)}</span>
      <span>${escapeHtml(horizon)}</span>
      <span>${item.alert_enabled ? 'Action Alert bật' : 'Chưa bật Alert'}</span>
      <b>Xem phân tích →</b>
    </a>`;
  }

  function renderWatchlists(root, watchlist) {
    const owned = watchlist.filter(item => item.owns_stock);
    const watching = watchlist.filter(item => !item.owns_stock);
    const ownedTarget = root.querySelector('[data-paid-owned-list]');
    const watchingTarget = root.querySelector('[data-paid-watch-list]');
    if (ownedTarget) {
      ownedTarget.innerHTML = owned.length
        ? owned.map(stockRow).join('')
        : '<div class="paid-empty">Chưa đánh dấu mã nào là đang sở hữu. Có thể cập nhật trong Tài khoản.</div>';
    }
    if (watchingTarget) {
      watchingTarget.innerHTML = watching.length
        ? watching.map(stockRow).join('')
        : '<div class="paid-empty">Chưa có mã chỉ theo dõi. Thêm mã trong Tài khoản để bảng Hôm nay ưu tiên đúng thứ bạn quan tâm.</div>';
    }
  }

  function recommendationAction(item) {
    return String(item.action || item.signal || item.recommendation_state || item.state || item.status || 'Theo dõi').replaceAll('_', ' ');
  }

  function rangeValue(item, lowKeys, highKeys) {
    const low = lowKeys.map(key => item?.[key]).find(value => value != null);
    const high = highKeys.map(key => item?.[key]).find(value => value != null);
    if (low == null && high == null) return '';
    if (low != null && high != null) return `${low}–${high}`;
    return String(low ?? high);
  }

  function renderActionCard(item, ownsStock = false) {
    const ticker = normalizeTicker(item.ticker || item.symbol);
    const buyZone = rangeValue(item, ['buy_zone_low', 'buy_low'], ['buy_zone_high', 'buy_high']);
    const stop = item.stop_loss ?? item.stop ?? item.invalidation_price;
    const target = item.target_near ?? item.target ?? item.target_price;
    const rr = item.risk_reward ?? item.rr;
    return `<article class="paid-action-card">
      <header><div><span class="panel-label">${ownsStock ? 'ĐANG SỞ HỮU' : 'CƠ HỘI'}</span><h3>${escapeHtml(ticker || '—')}</h3></div><strong>${escapeHtml(recommendationAction(item))}</strong></header>
      <div class="paid-action-metrics">
        <span>Buy Zone<b>${escapeHtml(buyZone || '—')}</b></span>
        <span>Stop<b>${escapeHtml(stop ?? '—')}</b></span>
        <span>Target<b>${escapeHtml(target ?? '—')}</b></span>
        <span>R/R<b>${escapeHtml(rr ?? '—')}</b></span>
      </div>
      <a class="text-link" href="${siteUrl(`co-phieu/${ticker}/`)}">Mở phân tích ${escapeHtml(ticker)} →</a>
    </article>`;
  }

  function renderActions(root, recommendations, watchlist) {
    const target = root.querySelector('[data-paid-actions]');
    const status = root.querySelector('[data-paid-decision-status]');
    if (!target) return;
    const asOf = recommendations?.snapshot?.as_of || recommendations?.as_of;
    setText(root, '[data-paid-snapshot]', formatSnapshot(asOf));

    if (!recommendations || isBlocked(recommendations)) {
      if (status) status.textContent = 'DATA GATE · CHƯA PHÁT HÀNH';
      target.innerHTML = `<div class="paid-gated">
        <strong>Chưa có dữ liệu quyết định đủ chuẩn để phát hành.</strong>
        <p>StockRadar không biến trạng thái thiếu dữ liệu thành “không có cơ hội”. Khi feed vượt Data Gate, hành động mua/giữ/gia tăng/hạ tỷ trọng sẽ xuất hiện tại đây theo đúng snapshot.</p>
      </div>`;
      return;
    }

    if (status) status.textContent = 'DECISION DATA · SẴN SÀNG';
    const items = Array.isArray(recommendations.items) ? recommendations.items : [];
    const watched = new Set(watchlist.map(item => normalizeTicker(item.ticker)));
    const owned = new Set(watchlist.filter(item => item.owns_stock).map(item => normalizeTicker(item.ticker)));
    const relevant = items.filter(item => watched.has(normalizeTicker(item.ticker || item.symbol)));
    relevant.sort((a, b) => Number(owned.has(normalizeTicker(b.ticker || b.symbol))) - Number(owned.has(normalizeTicker(a.ticker || a.symbol))));
    target.innerHTML = relevant.length
      ? relevant.map(item => renderActionCard(item, owned.has(normalizeTicker(item.ticker || item.symbol)))).join('')
      : '<div class="paid-empty">Không có hành động mới trên các mã bạn đang theo dõi tại snapshot này. Giữ nguyên kỷ luật; không cần giao dịch chỉ vì đã mở StockRadar.</div>';
  }

  function renderChanges(root, changes, watchlist) {
    const target = root.querySelector('[data-paid-changes]');
    if (!target) return;
    if (!changes || isBlocked(changes)) {
      target.innerHTML = '<div class="paid-empty">Feed thay đổi đang chờ Data Gate. Chưa phát hành thay đổi setup/dòng tiền cho quyết định giao dịch.</div>';
      return;
    }
    const watched = new Set(watchlist.map(item => normalizeTicker(item.ticker)));
    const items = (Array.isArray(changes.items) ? changes.items : []).filter(item => watched.has(normalizeTicker(item.ticker || item.symbol)));
    target.innerHTML = items.length ? items.slice(0, 8).map(item => {
      const ticker = normalizeTicker(item.ticker || item.symbol);
      const title = item.title || item.change || item.summary || 'Có thay đổi mới';
      const detail = item.detail || item.reason || item.description || '';
      return `<a class="paid-change-row" href="${siteUrl(`co-phieu/${ticker}/`)}"><strong>${escapeHtml(ticker)}</strong><span>${escapeHtml(title)}</span><small>${escapeHtml(detail)}</small><b>→</b></a>`;
    }).join('') : '<div class="paid-empty">Không có thay đổi mới trên watchlist tại snapshot hiện tại.</div>';
  }

  function renderPreferences(root, preferences) {
    const horizons = (preferences.preferred_horizons || []).map(value => HORIZON_LABELS[value] || value);
    const sectors = preferences.preferred_sectors || [];
    setText(root, '[data-paid-horizons]', horizons.length ? horizons.join(' · ') : 'Chưa chọn');
    setText(root, '[data-paid-sectors]', sectors.length ? sectors.join(' · ') : 'Chưa chọn');
  }

  async function mount() {
    const root = document.querySelector('[data-paid-dashboard]');
    if (!root) return;
    const guest = document.querySelector('[data-paid-dashboard-guest]');
    const content = root.querySelector('[data-paid-dashboard-content]');
    const loading = root.querySelector('[data-paid-dashboard-loading]');
    const client = getClient();

    if (!client) {
      if (loading) loading.textContent = 'Dịch vụ tài khoản chưa sẵn sàng.';
      return;
    }

    const { data: userData, error: userError } = await client.auth.getUser();
    const user = userData?.user;
    if (userError || !user) {
      if (loading) loading.hidden = true;
      if (guest) guest.hidden = false;
      return;
    }

    try {
      const [profile, preferences, watchlist, health, recommendations, changes] = await Promise.all([
        loadProfile(client, user.id),
        loadPreferences(client, user.id),
        loadWatchlist(client, user.id),
        loadEmailHealth(client),
        loadJson('public/data/recommendations.json'),
        loadJson('public/data/today-changes.json'),
      ]);

      renderPlan(root, profile, watchlist, health);
      renderPreferences(root, preferences);
      renderWatchlists(root, watchlist);
      renderActions(root, recommendations, watchlist);
      renderChanges(root, changes, watchlist);
      setText(root, '[data-paid-user-email]', user.email || 'Tài khoản');
      if (loading) loading.hidden = true;
      if (content) content.hidden = false;
    } catch (error) {
      if (loading) loading.textContent = 'Chưa thể tải bảng Hôm nay. Hãy mở lại trang hoặc kiểm tra phiên đăng nhập.';
    }
  }

  document.addEventListener('DOMContentLoaded', mount);
})();
