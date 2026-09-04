(() => {
  'use strict';

  const CONSENT_VERSION = '2026-09-04';
  const PREMIUM_TIERS = new Set(['TRIAL', 'PAID']);

  function getClient() {
    if (window.StockRadarEmailPreferenceClient) return window.StockRadarEmailPreferenceClient;
    const config = window.STOCKRADAR_AUTH_CONFIG || {};
    if (!window.supabase?.createClient || !config.configured) return null;
    window.StockRadarEmailPreferenceClient = window.supabase.createClient(
      config.supabaseUrl,
      config.supabasePublishableKey,
      {
        auth: {
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true,
          storageKey: 'stockradar-auth',
        },
      }
    );
    return window.StockRadarEmailPreferenceClient;
  }

  function setMessage(target, message, kind = '') {
    if (!target) return;
    target.className = `auth-message${kind ? ` ${kind}` : ''}`;
    target.textContent = message;
  }

  function isPremiumTier(value) {
    return PREMIUM_TIERS.has(String(value || '').toUpperCase());
  }

  function friendlyError(error) {
    const raw = String(error?.message || '').toLowerCase();
    if (raw.includes('premium product email requires trial or paid')) {
      return 'Email nội dung StockRadar chỉ dành cho Trial/Premium. Gói Free chỉ nhận email hệ thống của tài khoản.';
    }
    if (raw.includes('premium product email requires at least one selected product')) {
      return 'Chọn ít nhất một loại email trước khi bật gửi.';
    }
    if (raw.includes('product email requires active account')) {
      return 'Hãy xác minh email trước khi bật gửi email nội dung.';
    }
    if (raw.includes('row-level security') || raw.includes('permission')) {
      return 'Phiên đăng nhập không còn quyền lưu thay đổi. Hãy đăng nhập lại.';
    }
    return 'Chưa thể lưu tùy chọn email. Vui lòng thử lại.';
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
      .from('product_email_preferences')
      .select('enabled,daily_brief,event_alerts,post_session_digest,weekly_report,updated_at')
      .eq('user_id', userId)
      .maybeSingle();
    if (error) throw error;
    return data || {
      enabled: false,
      daily_brief: false,
      event_alerts: false,
      post_session_digest: false,
      weekly_report: false,
    };
  }

  async function loadLatestConsent(client, userId) {
    const { data, error } = await client
      .from('product_email_consent_events')
      .select('granted,document_version,recorded_at')
      .eq('user_id', userId)
      .order('recorded_at', { ascending: false })
      .limit(1)
      .maybeSingle();
    if (error) throw error;
    return data || null;
  }

  async function loadDeliveryHealth(client) {
    const { data, error } = await client.rpc('get_my_stockradar_email_health_v1');
    if (error) throw error;
    return data || null;
  }

  async function recordConsentIfChanged(client, userId, latest, granted) {
    if (latest && latest.granted === granted && latest.document_version === CONSENT_VERSION) return latest;
    const { data, error } = await client
      .from('product_email_consent_events')
      .insert({
        user_id: userId,
        granted,
        document_version: CONSENT_VERSION,
        source: 'ACCOUNT_CENTER',
      })
      .select('granted,document_version,recorded_at')
      .single();
    if (error) throw error;
    return data;
  }

  function formatHealthTime(value) {
    if (!value) return 'Chưa có';
    try {
      return new Intl.DateTimeFormat('vi-VN', {
        day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
      }).format(new Date(value));
    } catch (_) {
      return 'Chưa có';
    }
  }

  function emailKindLabel(value) {
    return ({
      DAILY_BRIEF: 'Daily 09:00',
      EVENT_ALERT: 'Action Alert',
      POST_SESSION_DIGEST: 'Cuối phiên',
      WEEKLY_REPORT: 'Weekly',
    })[String(value || '').toUpperCase()] || '';
  }

  function renderDeliveryHealth(health) {
    const root = document.querySelector('[data-premium-email-health]');
    if (!root || !health) return;

    const set = (selector, text) => {
      const target = root.querySelector(selector);
      if (target) target.textContent = text;
    };

    const premium = isPremiumTier(health.account_tier);
    const active = String(health.account_status || '').toUpperCase() === 'ACTIVE';
    const deliveryReady = Boolean(health.delivery_system_ready);
    const suppressed = String(health.suppression_reason || '').trim();

    set('[data-email-health-system]', !premium
      ? 'Nội dung Premium khóa'
      : suppressed
        ? 'Đang bị chặn gửi'
        : deliveryReady
          ? 'Hệ thống gửi hoạt động'
          : 'Hệ thống gửi chưa kích hoạt');
    set('[data-email-health-tier]', `${health.account_tier || 'FREE'} · ${health.account_status || 'PENDING'}`);
    set('[data-email-health-daily]', premium ? (health.daily_brief ? 'Đã chọn' : 'Tắt') : 'Cần Premium');
    set('[data-email-health-alerts]', premium ? (health.event_alerts ? 'Đã chọn' : 'Tắt') : 'Cần Premium');
    set('[data-email-health-watchlist]', `${Number(health.watchlist_count || 0)} mã`);
    set('[data-email-health-tickers]', `${Number(health.alert_ticker_count || 0)} mã`);

    const kind = emailKindLabel(health.last_email_kind);
    const last = health.last_email_at
      ? `${kind ? `${kind} · ` : ''}${health.last_delivery_status || '—'} · ${formatHealthTime(health.last_email_at)}`
      : 'Chưa có email';
    set('[data-email-health-last]', last);

    const note = root.querySelector('[data-email-health-note]');
    if (!note) return;
    if (!premium) {
      note.textContent = 'Gói Free chỉ nhận email hệ thống cần thiết cho tài khoản. Báo cáo hằng ngày, Action Alert, cuối phiên và tổng kết tuần thuộc Trial/Premium.';
    } else if (suppressed) {
      note.textContent = `Email đang bị suppression: ${suppressed}. Kiểm tra tùy chọn email hoặc liên hệ hỗ trợ nếu bạn không chủ động tắt.`;
    } else if (!active) {
      note.textContent = 'Xác minh tài khoản trước khi bật gửi. Các lựa chọn có thể được lưu nhưng chưa tạo quyền delivery.';
    } else if (!deliveryReady) {
      note.textContent = 'Cấu hình của bạn đã được lưu. Email production chỉ được gửi khi hệ thống delivery vượt đủ các cổng an toàn và được kích hoạt.';
    } else if (Number(health.alert_ticker_count || 0) === 0) {
      note.textContent = 'Premium đang hoạt động nhưng chưa có mã nào bật Action Alert. Bật cảnh báo ngay trên watchlist để StockRadar canh đúng mã bạn quan tâm.';
    } else {
      note.textContent = 'Email chỉ được tạo theo quyền gói, consent và trạng thái đủ điều kiện; không đổi trạng thái thì không tạo Action Alert riêng.';
    }
  }

  function renderState(root, user, profile, preferences, consent) {
    const active = String(profile.account_status || '').toUpperCase() === 'ACTIVE';
    const premium = isPremiumTier(profile.account_tier);
    const form = root.querySelector('[data-product-email-form]');
    if (!form) return;

    const master = form.elements.enabled;
    const daily = form.elements.daily_brief;
    const alerts = form.elements.event_alerts;
    const postSession = form.elements.post_session_digest;
    const weekly = form.elements.weekly_report;
    const button = form.querySelector('button[type="submit"]');
    const hasDeliverable = Boolean(
      premium && (
        preferences.daily_brief ||
        preferences.event_alerts ||
        preferences.post_session_digest ||
        preferences.weekly_report
      )
    );

    [daily, alerts, postSession, weekly].forEach(input => {
      if (input) input.disabled = !premium;
    });
    if (daily) daily.checked = Boolean(premium && preferences.daily_brief);
    if (alerts) alerts.checked = Boolean(premium && preferences.event_alerts);
    if (postSession) postSession.checked = Boolean(premium && preferences.post_session_digest);
    if (weekly) weekly.checked = Boolean(premium && preferences.weekly_report);
    if (master) {
      master.checked = Boolean(premium && preferences.enabled && active && hasDeliverable);
      master.disabled = !premium || !active;
    }
    if (button) button.disabled = !premium;

    const address = root.querySelector('[data-email-pref-address]');
    const verified = root.querySelector('[data-email-pref-verified]');
    const tier = root.querySelector('[data-email-pref-tier]');
    const consentTarget = root.querySelector('[data-email-pref-consent]');
    const delivery = root.querySelector('[data-email-pref-delivery]');
    const eligibility = root.querySelector('[data-email-pref-eligibility]');

    if (address) address.textContent = user.email || '—';
    if (verified) verified.textContent = user.email_confirmed_at ? 'Đã xác minh' : 'Chưa xác minh';
    if (tier) tier.textContent = profile.account_tier || 'FREE';
    if (consentTarget) consentTarget.textContent = premium && consent?.granted ? 'Đã đồng ý' : premium ? 'Chưa đồng ý' : 'Không áp dụng';
    if (delivery) {
      delivery.textContent = !premium
        ? 'Chỉ email hệ thống'
        : preferences.enabled && active && hasDeliverable
          ? 'Đã bật Premium'
          : consent?.granted
            ? 'Đã lưu lựa chọn'
            : 'Chưa bật';
    }
    if (eligibility) {
      eligibility.textContent = !premium
        ? 'Free · chỉ email hệ thống'
        : !active
          ? 'Cần xác minh email'
          : 'Premium · Daily + Action Alert + digest';
    }

    const note = root.querySelector('[data-product-email-tier-note]');
    if (note) {
      note.textContent = !premium
        ? 'Free chỉ nhận email giao dịch cần thiết cho tài khoản. Báo cáo hằng ngày và cảnh báo hành động được mở ở Trial/Premium.'
        : !active
          ? 'Xác minh email để có thể bật các email Premium đã chọn.'
          : 'Premium cho phép chọn riêng Daily 09:00, Action Alert, cuối phiên và Weekly. Action Alert chỉ được tạo khi trạng thái thay đổi đủ điều kiện.';
    }
  }

  async function mountEmailPreferences() {
    const root = document.querySelector('[data-product-email-preferences]');
    if (!root) return;

    const client = getClient();
    const status = root.querySelector('[data-product-email-status]');
    if (!client) {
      setMessage(status, 'Dịch vụ tài khoản chưa sẵn sàng.', 'error');
      return;
    }

    const { data: userData, error: userError } = await client.auth.getUser();
    const user = userData?.user;
    if (userError || !user) {
      setMessage(status, 'Đăng nhập để quản lý email StockRadar.', 'error');
      return;
    }

    const form = root.querySelector('[data-product-email-form]');
    const message = form?.querySelector('[data-auth-message]');
    let profile;
    let preferences;
    let consent;

    const refreshHealth = async () => {
      try { renderDeliveryHealth(await loadDeliveryHealth(client)); } catch (_) {}
    };

    try {
      [profile, preferences, consent] = await Promise.all([
        loadProfile(client, user.id),
        loadPreferences(client, user.id),
        loadLatestConsent(client, user.id),
      ]);
      renderState(root, user, profile, preferences, consent);
      await refreshHealth();
      setMessage(status, isPremiumTier(profile.account_tier)
        ? 'Tùy chọn email Premium được lưu theo tài khoản và có thể thay đổi bất kỳ lúc nào.'
        : 'Gói Free chỉ nhận email hệ thống. Nâng Trial/Premium để bật báo cáo và Action Alert.', 'success');
    } catch (error) {
      setMessage(status, friendlyError(error), 'error');
      return;
    }

    form?.addEventListener('submit', async event => {
      event.preventDefault();
      const premium = isPremiumTier(profile.account_tier);
      if (!premium) {
        setMessage(message, 'Email nội dung StockRadar chỉ dành cho Trial/Premium.', 'error');
        return;
      }

      const dailyBrief = Boolean(form.elements.daily_brief?.checked);
      const eventAlerts = Boolean(form.elements.event_alerts?.checked);
      const postSessionDigest = Boolean(form.elements.post_session_digest?.checked);
      const weeklyReport = Boolean(form.elements.weekly_report?.checked);
      const selectedAny = dailyBrief || eventAlerts || postSessionDigest || weeklyReport;
      const active = String(profile.account_status || '').toUpperCase() === 'ACTIVE';
      const masterRequested = Boolean(form.elements.enabled?.checked);

      if (masterRequested && !selectedAny) {
        setMessage(message, 'Chọn ít nhất một loại email trước khi bật gửi.', 'error');
        return;
      }

      const enabled = Boolean(active && masterRequested && selectedAny);
      const granted = selectedAny;
      const button = form.querySelector('button[type="submit"]');
      if (button) button.disabled = true;
      setMessage(message, 'Đang lưu…');

      try {
        const { error } = await client.from('product_email_preferences').upsert({
          user_id: user.id,
          enabled,
          daily_brief: dailyBrief,
          event_alerts: eventAlerts,
          post_session_digest: postSessionDigest,
          weekly_report: weeklyReport,
        }, { onConflict: 'user_id' });
        if (error) throw error;

        consent = await recordConsentIfChanged(client, user.id, consent, granted);
        preferences = await loadPreferences(client, user.id);
        renderState(root, user, profile, preferences, consent);
        await refreshHealth();

        if (!selectedAny) {
          setMessage(message, 'Đã rút đăng ký email nội dung Premium.', 'success');
        } else if (!active) {
          setMessage(message, 'Đã lưu lựa chọn. Xác minh email để có thể bật gửi theo quyền gói.', 'success');
        } else if (enabled) {
          setMessage(message, 'Đã lưu các email Premium bạn chọn. Action Alert chỉ phát sinh khi trạng thái thực sự thay đổi.', 'success');
        } else {
          setMessage(message, 'Đã lưu loại email quan tâm; gửi email hiện đang tắt.', 'success');
        }
      } catch (error) {
        setMessage(message, friendlyError(error), 'error');
      } finally {
        if (button) button.disabled = !isPremiumTier(profile.account_tier);
      }
    });

    const watchlistTarget = document.querySelector('[data-account-watchlist]');
    if (watchlistTarget) {
      let refreshTimer = null;
      new MutationObserver(() => {
        if (refreshTimer) clearTimeout(refreshTimer);
        refreshTimer = setTimeout(refreshHealth, 120);
      }).observe(watchlistTarget, { childList: true, subtree: true });
    }
  }

  document.addEventListener('DOMContentLoaded', mountEmailPreferences);
})();