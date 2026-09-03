(() => {
  'use strict';

  const CONSENT_VERSION = '2026-09-03';
  const FALLBACK_SUPABASE_URL = 'https://xamviatbxufjlpiwhebb.supabase.co';

  function setMessage(target, message, kind = '') {
    if (!target) return;
    target.className = `email-interest-message${kind ? ` ${kind}` : ''}`;
    target.textContent = message;
  }

  function endpoint() {
    const authConfig = window.STOCKRADAR_AUTH_CONFIG || {};
    const base = authConfig.supabaseUrl || FALLBACK_SUPABASE_URL;
    return `${String(base).replace(/\/$/, '')}/functions/v1/email-interest`;
  }

  function validEmail(value) {
    return /^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$/i.test(value);
  }

  async function submitInterest(form) {
    const email = String(form.elements.email?.value || '').trim().toLowerCase();
    const dailyBrief = Boolean(form.elements.daily_brief?.checked);
    const eventAlerts = Boolean(form.elements.event_alerts?.checked);
    const privacyAccepted = Boolean(form.elements.privacy?.checked);
    const company = String(form.elements.company?.value || '');
    const message = form.querySelector('[data-email-interest-message]');
    const button = form.querySelector('button[type="submit"]');

    if (!validEmail(email)) {
      setMessage(message, 'Nhập email hợp lệ để ghi nhận nhu cầu Premium.', 'error');
      form.elements.email?.focus();
      return;
    }
    if (!dailyBrief && !eventAlerts) {
      setMessage(message, 'Chọn ít nhất Báo cáo Premium hằng ngày hoặc Cảnh báo hành động Premium.', 'error');
      return;
    }
    if (!privacyAccepted) {
      setMessage(message, 'Cần đồng ý lưu email và lựa chọn quan tâm trước khi tiếp tục.', 'error');
      return;
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    if (button) button.disabled = true;
    setMessage(message, 'Đang ghi nhận nhu cầu…');

    try {
      const response = await fetch(endpoint(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          daily_brief: dailyBrief,
          event_alerts: eventAlerts,
          privacy_accepted: true,
          consent_version: CONSENT_VERSION,
          company,
        }),
        signal: controller.signal,
        credentials: 'omit',
        cache: 'no-store',
      });

      let payload = {};
      try { payload = await response.json(); } catch (_) {}
      if (!response.ok || payload.accepted !== true) {
        throw new Error(payload.message || 'Chưa thể ghi nhận nhu cầu Premium lúc này.');
      }

      form.reset();
      setMessage(
        message,
        payload.message || 'Đã ghi nhận email ở trạng thái chờ xác minh. Bước này chưa kích hoạt báo cáo hoặc cảnh báo Premium.',
        'success'
      );
    } catch (error) {
      const text = error?.name === 'AbortError'
        ? 'Kết nối ghi nhận email quá thời gian. Vui lòng thử lại.'
        : String(error?.message || 'Chưa thể ghi nhận nhu cầu Premium lúc này.');
      setMessage(message, text, 'error');
    } finally {
      clearTimeout(timeout);
      if (button) button.disabled = false;
    }
  }

  function mount() {
    document.querySelectorAll('[data-email-interest-form]').forEach(form => {
      if (form.dataset.emailInterestMounted === '1') return;
      form.dataset.emailInterestMounted = '1';
      form.addEventListener('submit', event => {
        event.preventDefault();
        submitInterest(form);
      });
    });
  }

  document.addEventListener('DOMContentLoaded', mount);
})();