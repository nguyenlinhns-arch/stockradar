(() => {
  'use strict';

  const CONSENT_VERSION = '2026-09-04';
  const FALLBACK_SUPABASE_URL = 'https://xamviatbxufjlpiwhebb.supabase.co';
  const LEAD_CAPTURED_KEY = 'sr_email_lead_captured';
  const PENDING_LEAD_EMAIL_KEY = 'sr_pending_lead_email';

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

  function attribution() {
    const params = new URLSearchParams(window.location.search);
    let referrerHost = '';
    try { referrerHost = document.referrer ? new URL(document.referrer).hostname : ''; } catch (_) {}
    return {
      source_path: String(window.location.pathname || '/').slice(0, 256),
      utm_source: String(params.get('utm_source') || '').slice(0, 120),
      utm_campaign: String(params.get('utm_campaign') || '').slice(0, 160),
      referrer_host: String(referrerHost || '').slice(0, 253),
    };
  }

  function rememberLead(email) {
    try { localStorage.setItem(LEAD_CAPTURED_KEY, '1'); } catch (_) {}
    try { sessionStorage.setItem(PENDING_LEAD_EMAIL_KEY, email); } catch (_) {}
  }

  function removeNextStep(form) {
    form.querySelector('[data-email-interest-next]')?.remove();
  }

  function renderNextStep(form) {
    removeNextStep(form);
    const rawHref = String(form.dataset.nextHref || '').trim();
    if (!rawHref) return;
    const link = document.createElement('a');
    link.className = 'email-interest-next';
    link.dataset.emailInterestNext = '';
    link.href = new URL(rawHref, document.baseURI).toString();
    link.textContent = String(form.dataset.nextLabel || 'Tiếp tục');
    const message = form.querySelector('[data-email-interest-message]');
    message?.insertAdjacentElement('afterend', link);
  }

  async function submitInterest(form) {
    const email = String(form.elements.email?.value || '').trim().toLowerCase();
    const dailyBrief = Boolean(form.elements.daily_brief?.checked);
    const eventAlerts = Boolean(form.elements.event_alerts?.checked);
    const privacyAccepted = Boolean(form.elements.privacy?.checked);
    const company = String(form.elements.company?.value || '');
    const message = form.querySelector('[data-email-interest-message]');
    const button = form.querySelector('button[type="submit"]');

    removeNextStep(form);
    if (!validEmail(email)) {
      setMessage(message, 'Nhập email hợp lệ để ghi nhận nhu cầu nhận bản tin/cảnh báo StockRadar.', 'error');
      form.elements.email?.focus();
      return;
    }
    if (!dailyBrief && !eventAlerts) {
      setMessage(message, 'Chọn ít nhất bản rà soát 09:00 hoặc cảnh báo điểm mua/bán Premium.', 'error');
      return;
    }
    if (!privacyAccepted) {
      setMessage(message, 'Cần đồng ý lưu email và lựa chọn quan tâm trước khi tiếp tục.', 'error');
      return;
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    if (button) button.disabled = true;
    setMessage(message, 'Đang ghi nhận email…');

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
          ...attribution(),
        }),
        signal: controller.signal,
        credentials: 'omit',
        cache: 'no-store',
      });

      let payload = {};
      try { payload = await response.json(); } catch (_) {}
      if (!response.ok || payload.accepted !== true) {
        throw new Error(payload.message || 'Chưa thể ghi nhận nhu cầu email lúc này.');
      }

      rememberLead(email);
      setMessage(
        message,
        payload.message || 'Đã ghi nhận email ở trạng thái chờ xác minh. Bản tin 09:00 cần quyền Free trở lên; cảnh báo mua/bán cần quyền Premium.',
        'success'
      );
      renderNextStep(form);
      form.querySelectorAll('input[type="checkbox"]').forEach(input => { input.checked = false; });
    } catch (error) {
      const text = error?.name === 'AbortError'
        ? 'Kết nối ghi nhận email quá thời gian. Vui lòng thử lại.'
        : String(error?.message || 'Chưa thể ghi nhận nhu cầu email lúc này.');
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