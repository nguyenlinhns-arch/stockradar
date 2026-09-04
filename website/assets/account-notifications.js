(() => {
  'use strict';

  const LIMIT = 30;
  const REFRESH_MS = 60_000;
  const HORIZON_LABELS = Object.freeze({
    SHORT_TERM: 'Ngắn hạn',
    MEDIUM_TERM: 'Trung hạn',
    LONG_TERM: 'Dài hạn',
    ACCUMULATION: 'Tích sản',
  });
  const STATE_LABELS = Object.freeze({
    WAIT: 'Chờ',
    BUY: 'Mua',
    HOLD: 'Giữ',
    ADD: 'Nhồi lệnh',
    REDUCE: 'Hạ tỷ trọng',
    SELL: 'Bán / cắt lỗ',
  });

  let refreshTimer = 0;
  let inFlight = false;

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

  function formatDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '—';
    return new Intl.DateTimeFormat('vi-VN', {
      dateStyle: 'short',
      timeStyle: 'short',
      timeZone: 'Asia/Ho_Chi_Minh',
    }).format(date);
  }

  function setStatus(root, text, kind = '') {
    const target = root.querySelector('[data-notification-status]');
    if (!target) return;
    target.className = `auth-message${kind ? ` ${kind}` : ''}`;
    target.textContent = text;
  }

  function setUnread(root, count) {
    const badge = root.querySelector('[data-notification-unread]');
    const label = root.querySelector('[data-notification-unread-label]');
    if (badge) {
      badge.textContent = String(count);
      badge.hidden = count < 1;
    }
    if (label) label.textContent = count ? `${count} chưa đọc` : 'Đã đọc hết';
  }

  function buildMeta(item) {
    const parts = [];
    if (item.horizon) parts.push(HORIZON_LABELS[item.horizon] || item.horizon);
    if (item.lane === 'HOLDING') parts.push('Đang nắm giữ');
    if (item.lane === 'NEW_POSITION') parts.push('Mua mới');
    parts.push(formatDate(item.created_at));
    return parts.join(' · ');
  }

  function buildTransition(item) {
    const previous = STATE_LABELS[item.previous_state] || item.previous_state || '—';
    const current = STATE_LABELS[item.current_state] || item.current_state || '—';
    return `${previous} → ${current}`;
  }

  function createNotificationCard(item, onRead) {
    const article = document.createElement('article');
    article.className = `stockradar-notification${item.read_at ? '' : ' is-unread'}`;
    article.dataset.notificationId = item.id;

    const top = document.createElement('div');
    top.className = 'stockradar-notification-top';

    const textWrap = document.createElement('div');
    const eyebrow = document.createElement('div');
    eyebrow.className = 'stockradar-notification-eyebrow';

    const tickerLink = document.createElement('a');
    tickerLink.className = 'stockradar-notification-ticker';
    tickerLink.href = siteUrl(`co-phieu/${String(item.ticker || '').toUpperCase()}/`);
    tickerLink.textContent = String(item.ticker || '').toUpperCase();
    eyebrow.append(tickerLink);

    const transition = document.createElement('span');
    transition.className = 'stockradar-notification-transition';
    transition.textContent = buildTransition(item);
    eyebrow.append(transition);

    const title = document.createElement('h3');
    title.textContent = item.title || 'Cảnh báo StockRadar';

    const body = document.createElement('p');
    body.textContent = item.body || '';

    const meta = document.createElement('p');
    meta.className = 'stockradar-notification-meta';
    meta.textContent = buildMeta(item);

    textWrap.append(eyebrow, title, body, meta);
    top.append(textWrap);

    if (!item.read_at) {
      const unreadDot = document.createElement('span');
      unreadDot.className = 'stockradar-notification-dot';
      unreadDot.setAttribute('aria-label', 'Chưa đọc');
      top.append(unreadDot);
    }

    const actions = document.createElement('div');
    actions.className = 'stockradar-notification-actions';

    const openLink = document.createElement('a');
    openLink.className = 'button button-secondary button-small';
    openLink.href = tickerLink.href;
    openLink.textContent = 'Mở mã';
    actions.append(openLink);

    if (!item.read_at) {
      const readButton = document.createElement('button');
      readButton.className = 'button button-secondary button-small';
      readButton.type = 'button';
      readButton.textContent = 'Đã đọc';
      readButton.addEventListener('click', () => onRead(item.id, readButton));
      actions.append(readButton);
    }

    article.append(top, actions);
    return article;
  }

  function renderNotifications(root, items, onRead) {
    const list = root.querySelector('[data-notification-list]');
    if (!list) return;
    list.textContent = '';

    const active = items.filter(item => !item.expires_at || new Date(item.expires_at).getTime() > Date.now());
    const unread = active.filter(item => !item.read_at).length;
    setUnread(root, unread);

    if (!active.length) {
      const empty = document.createElement('div');
      empty.className = 'account-empty-state stockradar-notification-empty';
      const strong = document.createElement('strong');
      strong.textContent = 'Chưa có cảnh báo hành động.';
      const text = document.createElement('p');
      text.textContent = 'StockRadar chỉ hiển thị tại đây khi trạng thái đã được xác nhận đổi sang Mua, Nhồi lệnh, Hạ tỷ trọng hoặc Bán/cắt lỗ và toàn bộ gate dữ liệu đều đạt chuẩn.';
      empty.append(strong, text);
      list.append(empty);
      return;
    }

    active.forEach(item => list.append(createNotificationCard(item, onRead)));
  }

  async function loadNotifications(client) {
    const { data, error } = await client
      .from('stockradar_notifications')
      .select('id,ticker,horizon,lane,previous_state,current_state,title,body,payload,created_at,expires_at,read_at')
      .order('created_at', { ascending: false })
      .limit(LIMIT);
    if (error) throw error;
    return data || [];
  }

  async function markRead(client, id) {
    const { data, error } = await client.rpc('mark_stockradar_notification_read_v1', {
      p_notification_id: id,
    });
    if (error) throw error;
    if (data !== true) throw new Error('NOTIFICATION_NOT_UPDATED');
  }

  async function mountNotifications() {
    const root = document.querySelector('[data-stockradar-notifications]');
    if (!root) return;

    const client = getClient();
    if (!client) {
      setStatus(root, 'Dịch vụ cảnh báo chưa sẵn sàng.', 'error');
      return;
    }

    const { data: userData, error: userError } = await client.auth.getUser();
    if (userError || !userData?.user) {
      setStatus(root, 'Đăng nhập để xem cảnh báo của bạn.', 'error');
      return;
    }

    const refreshButton = root.querySelector('[data-notification-refresh]');

    const refresh = async ({ quiet = false } = {}) => {
      if (inFlight) return;
      inFlight = true;
      if (!quiet) setStatus(root, 'Đang cập nhật cảnh báo…');
      if (refreshButton) refreshButton.disabled = true;
      try {
        const items = await loadNotifications(client);
        renderNotifications(root, items, async (id, button) => {
          button.disabled = true;
          button.textContent = 'Đang lưu…';
          try {
            await markRead(client, id);
            await refresh({ quiet: true });
          } catch (error) {
            console.error('StockRadar notification read failed', error);
            button.disabled = false;
            button.textContent = 'Thử lại';
            setStatus(root, 'Chưa thể đánh dấu đã đọc. Vui lòng thử lại.', 'error');
          }
        });
        const newest = items[0]?.created_at ? ` · mới nhất ${formatDate(items[0].created_at)}` : '';
        setStatus(root, `Cảnh báo được bảo vệ theo tài khoản${newest}.`, 'success');
      } catch (error) {
        console.error('StockRadar notifications failed', error);
        setUnread(root, 0);
        setStatus(root, 'Chưa thể tải cảnh báo. Phiên đăng nhập có thể đã hết hạn.', 'error');
      } finally {
        inFlight = false;
        if (refreshButton) refreshButton.disabled = false;
      }
    };

    refreshButton?.addEventListener('click', () => refresh());
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') refresh({ quiet: true });
    });

    await refresh();
    window.clearInterval(refreshTimer);
    refreshTimer = window.setInterval(() => {
      if (document.visibilityState === 'visible') refresh({ quiet: true });
    }, REFRESH_MS);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mountNotifications, { once: true });
  } else {
    mountNotifications();
  }
})();
