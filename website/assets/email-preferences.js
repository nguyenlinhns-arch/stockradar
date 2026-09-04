(() => {
  'use strict';

  const CONSENT_VERSION = '2026-09-04';
  const KNOWN_TIERS = new Set(['FREE', 'TRIAL', 'PAID']);
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

  function friendlyError(error) {
    const raw = String(error?.message || '').toLowerCase();
    if (raw.includes('free product email requires daily brief')) {
      return 'Gói Free chỉ có thể bật gửi khi chọn bản rà soát 09:00. Cảnh báo mua/bán thuộc quyền Premium.';
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

  function renderState(root, user, profile, preferences, consent) {
    const active = profile.account_status === 'ACTIVE' && KNOWN_TIERS.has(profile.account_tier);
    const premium = PREMIUM_TIERS.has(profile.account_tier);
    const free = profile.account_tier === 'FREE';
    const form = root.querySelector('[data-product-email-form]');
    const master = form?.elements?.enabled;
    const daily = form?.elements?.daily_brief;
    const alerts = form?.elements?.event_alerts;
    const hasDeliverable = Boolean(preferences.daily_brief || (premium && preferences.event_alerts));

    if (master) {
      master.checked = Boolean(preferences.enabled && active && hasDeliverable);
      master.disabled = !active;
    }
    if (daily) daily.checked = Boolean(preferences.daily_brief);
    if (alerts) alerts.checked = Boolean(preferences.event_alerts);

    const address = root.querySelector('[data-email-pref-address]');
    const verified = root.querySelector('[data-email-pref-verified]');
    const tier = root.querySelector('[data-email-pref-tier]');
    const consentTarget = root.querySelector('[data-email-pref-consent]');
    const delivery = root.querySelector('[data-email-pref-delivery]');
    const eligibility = root.querySelector('[data-email-pref-eligibility]');

    if (address) address.textContent = user.email || '—';
    if (verified) verified.textContent = user.email_confirmed_at ? 'Đã xác minh' : 'Chưa xác minh';
    if (tier) tier.textContent = profile.account_tier || 'FREE';
    if (consentTarget) consentTarget.textContent = consent?.granted ? 'Đã đồng ý' : 'Chưa đồng ý';
    if (delivery) {
      delivery.textContent = preferences.enabled && active && hasDeliverable
        ? (premium ? 'Đã bật Premium' : 'Đã bật bản tin 09:00')
        : consent?.granted
          ? 'Đã lưu lựa chọn'
          : 'Chưa bật';
    }
    if (eligibility) {
      eligibility.textContent = !active
        ? 'Cần xác minh email'
        : premium
          ? 'Premium · bản tin 09:00 + cảnh báo trong phiên'
          : 'Free · bản tin 09:00';
    }

    const note = root.querySelector('[data-product-email-tier-note]');
    if (note) {
      note.textContent = !active
        ? 'Xác minh email để bật bản rà soát 09:00. Cảnh báo điểm mua/bán chỉ được gửi khi tài khoản có quyền Premium.'
        : premium
          ? 'Premium nhận bản tin 09:00 và có thể bật cảnh báo điểm mua/bán trong phiên tại các mốc quét chính thức khi tín hiệu đủ chuẩn.'
          : 'Free nhận bản rà soát thị trường cơ bản lúc 09:00 khi bạn bật gửi. Cảnh báo điểm mua/bán trong phiên chỉ dành cho Premium.';
    }

    if (free && alerts) {
      alerts.title = 'Bạn có thể lưu nhu cầu; cảnh báo điểm mua/bán chỉ được gửi sau khi nâng Premium.';
    }
  }

  async function loadWatchlistAlertState(client, userId) {
    const { data, error } = await client
      .from('watchlist_items')
      .select('id,alert_enabled')
      .eq('user_id', userId)
      .is('removed_at', null);
    if (error) throw error;
    return new Map((data || []).map(item => [item.id, Boolean(item.alert_enabled)]));
  }

  function mountWatchlistToggles(target, state) {
    if (!target) return;
    target.querySelectorAll('.watchlist-row[data-watchlist-id]').forEach(row => {
      if (row.querySelector('[data-watchlist-alert-toggle]')) return;
      const id = row.dataset.watchlistId;
      if (!id || !state.has(id)) return;
      const label = document.createElement('label');
      label.className = 'email-watch-toggle';
      label.innerHTML = `<input type="checkbox" data-watchlist-alert-toggle ${state.get(id) ? 'checked' : ''}><span>Cảnh báo mã này</span>`;
      const removeButton = row.querySelector('[data-watchlist-remove]');
      if (removeButton) row.insertBefore(label, removeButton);
      else row.append(label);
    });
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

    try {
      [profile, preferences, consent] = await Promise.all([
        loadProfile(client, user.id),
        loadPreferences(client, user.id),
        loadLatestConsent(client, user.id),
      ]);
      renderState(root, user, profile, preferences, consent);
      setMessage(status, 'Tùy chọn email được lưu theo tài khoản và có thể thay đổi bất kỳ lúc nào.', 'success');
    } catch (error) {
      setMessage(status, friendlyError(error), 'error');
      return;
    }

    form?.addEventListener('submit', async event => {
      event.preventDefault();
      const dailyBrief = Boolean(form.elements.daily_brief?.checked);
      const eventAlerts = Boolean(form.elements.event_alerts?.checked);
      const selectedAny = dailyBrief || eventAlerts;
      const active = profile.account_status === 'ACTIVE' && KNOWN_TIERS.has(profile.account_tier);
      const premium = PREMIUM_TIERS.has(profile.account_tier);
      const free = profile.account_tier === 'FREE';
      const masterRequested = Boolean(form.elements.enabled?.checked);

      if (masterRequested && !selectedAny) {
        setMessage(message, 'Chọn ít nhất một loại email trước khi bật gửi.', 'error');
        return;
      }
      if (masterRequested && free && !dailyBrief) {
        setMessage(message, 'Gói Free cần chọn bản rà soát 09:00 để bật gửi. Cảnh báo mua/bán chỉ dành cho Premium.', 'error');
        return;
      }

      const deliverableSelected = Boolean(dailyBrief || (premium && eventAlerts));
      const enabled = Boolean(active && masterRequested && deliverableSelected);
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
          post_session_digest: false,
          weekly_report: false,
        }, { onConflict: 'user_id' });
        if (error) throw error;

        consent = await recordConsentIfChanged(client, user.id, consent, granted);
        preferences = await loadPreferences(client, user.id);
        renderState(root, user, profile, preferences, consent);

        if (!selectedAny) {
          setMessage(message, 'Đã rút đăng ký email nội dung.', 'success');
        } else if (!active) {
          setMessage(message, 'Đã lưu lựa chọn. Xác minh email để có thể bật gửi theo quyền gói.', 'success');
        } else if (enabled && premium) {
          setMessage(message, 'Đã bật bản tin 09:00 và các email Premium bạn chọn.', 'success');
        } else if (enabled && free) {
          setMessage(message, eventAlerts
            ? 'Đã bật bản rà soát 09:00. Nhu cầu cảnh báo mua/bán đã được lưu và chỉ có hiệu lực sau khi nâng Premium.'
            : 'Đã bật bản rà soát thị trường 09:00 cho tài khoản Free.', 'success');
        } else {
          setMessage(message, 'Đã lưu loại email quan tâm; gửi email hiện đang tắt.', 'success');
        }
      } catch (error) {
        setMessage(message, friendlyError(error), 'error');
      } finally {
        if (button) button.disabled = false;
      }
    });

    const watchlistTarget = document.querySelector('[data-account-watchlist]');
    if (!watchlistTarget) return;

    let alertState = new Map();
    let refreshTimer = null;
    const refreshToggles = async () => {
      try {
        alertState = await loadWatchlistAlertState(client, user.id);
        mountWatchlistToggles(watchlistTarget, alertState);
      } catch (_) {}
    };
    const scheduleRefresh = () => {
      if (refreshTimer) return;
      refreshTimer = setTimeout(async () => {
        refreshTimer = null;
        await refreshToggles();
      }, 80);
    };

    await refreshToggles();
    const observer = new MutationObserver(scheduleRefresh);
    observer.observe(watchlistTarget, { childList: true, subtree: true });

    watchlistTarget.addEventListener('change', async event => {
      const toggle = event.target.closest('[data-watchlist-alert-toggle]');
      if (!toggle) return;
      const row = toggle.closest('[data-watchlist-id]');
      const id = row?.dataset.watchlistId;
      if (!id) return;
      const nextValue = Boolean(toggle.checked);
      toggle.disabled = true;
      try {
        const { error } = await client
          .from('watchlist_items')
          .update({ alert_enabled: nextValue })
          .eq('id', id)
          .eq('user_id', user.id);
        if (error) throw error;
        alertState.set(id, nextValue);
        setMessage(status, nextValue
          ? 'Đã lưu mã ưu tiên nhận cảnh báo. Gửi cảnh báo qua email chỉ hoạt động khi tài khoản có quyền Premium và email toàn cục đang bật.'
          : 'Đã tắt cảnh báo riêng cho mã này.', 'success');
      } catch (error) {
        toggle.checked = !nextValue;
        setMessage(status, friendlyError(error), 'error');
      } finally {
        toggle.disabled = false;
      }
    });
  }

  document.addEventListener('DOMContentLoaded', mountEmailPreferences);
})();