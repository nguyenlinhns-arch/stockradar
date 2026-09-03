(() => {
  'use strict';

  const SIGNUP_OTP_DEADLINE_KEY = 'sr_signup_otp_resend_deadline';
  const LOGIN_OTP_DEADLINE_KEY = 'sr_login_otp_resend_deadline';
  const LOGIN_VERIFY_EMAIL_KEY = 'sr_login_verify_email';
  const OTP_RESEND_SECONDS = 60;

  function setMessage(target, message, kind = '') {
    if (!target) return;
    target.className = `auth-message${kind ? ` ${kind}` : ''}`;
    target.textContent = message;
  }

  function normalizeEmail(value) {
    return String(value || '').trim().toLowerCase();
  }

  function normalizeOtp(value) {
    return String(value || '').replace(/\D/g, '').slice(0, 6);
  }

  function maskEmail(value) {
    const email = normalizeEmail(value);
    const [local, domain] = email.split('@');
    if (!local || !domain) return email;
    const visible = local.length <= 2 ? local.slice(0, 1) : local.slice(0, 2);
    return `${visible}***@${domain}`;
  }

  function getDeadline(key) {
    try { return Number(sessionStorage.getItem(key) || 0); } catch (_) { return 0; }
  }

  function setDeadline(key, seconds = OTP_RESEND_SECONDS) {
    const deadline = Date.now() + seconds * 1000;
    try { sessionStorage.setItem(key, String(deadline)); } catch (_) {}
    return deadline;
  }

  function clearDeadline(key) {
    try { sessionStorage.removeItem(key); } catch (_) {}
  }

  function remainingSeconds(key) {
    return Math.max(0, Math.ceil((getDeadline(key) - Date.now()) / 1000));
  }

  function runPersistentCooldown(button, key) {
    if (!button) return;
    if (!button.dataset.defaultLabel) button.dataset.defaultLabel = button.textContent.trim();
    if (button._srPersistentOtpTimer) clearInterval(button._srPersistentOtpTimer);
    const render = () => {
      const left = remainingSeconds(key);
      if (left <= 0) {
        clearInterval(button._srPersistentOtpTimer);
        button._srPersistentOtpTimer = null;
        button.disabled = false;
        button.textContent = button.dataset.defaultLabel;
        return;
      }
      button.disabled = true;
      button.textContent = `Gửi lại sau ${left}s`;
    };
    render();
    if (remainingSeconds(key) > 0) button._srPersistentOtpTimer = setInterval(render, 1000);
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

  function wirePersistentSignupOtpCooldown() {
    const panel = document.querySelector('[data-auth-signup-otp-form]');
    const resend = panel?.querySelector('[data-auth-otp-resend]');
    if (!panel || !resend) return;

    runPersistentCooldown(resend, SIGNUP_OTP_DEADLINE_KEY);
    resend.addEventListener('click', () => {
      setDeadline(SIGNUP_OTP_DEADLINE_KEY);
      runPersistentCooldown(resend, SIGNUP_OTP_DEADLINE_KEY);
    }, { capture: true });

    const observer = new MutationObserver(() => {
      if (!panel.hidden) {
        if (remainingSeconds(SIGNUP_OTP_DEADLINE_KEY) <= 0) setDeadline(SIGNUP_OTP_DEADLINE_KEY);
        runPersistentCooldown(resend, SIGNUP_OTP_DEADLINE_KEY);
      }
    });
    observer.observe(panel, { attributes: true, attributeFilter: ['hidden'] });
  }

  function wireMaskedOtpEmail() {
    const target = document.querySelector('[data-auth-otp-email]');
    if (!target) return;
    let updating = false;
    const render = () => {
      if (updating) return;
      const raw = target.textContent.trim();
      if (!raw.includes('@') || raw.includes('***')) return;
      updating = true;
      target.textContent = maskEmail(raw);
      updating = false;
    };
    render();
    new MutationObserver(render).observe(target, { childList: true, characterData: true, subtree: true });
  }

  function wireLoginOtpVerification() {
    const form = document.querySelector('[data-auth-login-otp-form]');
    if (!form) return;
    const sendButton = form.querySelector('[data-auth-login-otp-send]');
    const message = form.querySelector('[data-auth-message]');
    const emailInput = form.elements.email;
    const otpInput = form.elements.otp;
    const details = form.closest('details');
    const mainEmail = document.querySelector('[data-auth-login-form] input[name="email"]');

    try {
      const stored = normalizeEmail(sessionStorage.getItem(LOGIN_VERIFY_EMAIL_KEY));
      if (stored) emailInput.value = stored;
    } catch (_) {}

    details?.addEventListener('toggle', () => {
      if (details.open && !emailInput.value && mainEmail?.value) emailInput.value = normalizeEmail(mainEmail.value);
    });
    otpInput?.addEventListener('input', () => { otpInput.value = normalizeOtp(otpInput.value); });
    runPersistentCooldown(sendButton, LOGIN_OTP_DEADLINE_KEY);

    sendButton?.addEventListener('click', async () => {
      const email = normalizeEmail(emailInput.value);
      if (!email || !email.includes('@')) return setMessage(message, 'Nhập email hợp lệ trước khi gửi OTP.', 'error');
      const client = getClient();
      if (!client) return setMessage(message, 'Dịch vụ xác thực chưa sẵn sàng.', 'error');
      sendButton.disabled = true;
      try {
        const { error } = await client.auth.resend({
          type: 'signup',
          email,
          options: { emailRedirectTo: new URL('tai-khoan/?verified=1', document.baseURI).toString() },
        });
        if (error) throw error;
        try { sessionStorage.setItem(LOGIN_VERIFY_EMAIL_KEY, email); } catch (_) {}
        setDeadline(LOGIN_OTP_DEADLINE_KEY);
        runPersistentCooldown(sendButton, LOGIN_OTP_DEADLINE_KEY);
        setMessage(message, 'Đã gửi OTP xác minh. Kiểm tra cả Inbox và Spam.', 'success');
        otpInput?.focus();
      } catch (_) {
        sendButton.disabled = false;
        setMessage(message, 'Chưa thể gửi OTP. Có thể tài khoản đã xác minh hoặc đang bị giới hạn gửi lại.', 'error');
      }
    });

    form.addEventListener('submit', async event => {
      event.preventDefault();
      const email = normalizeEmail(emailInput.value);
      const token = normalizeOtp(otpInput.value);
      if (!email || !email.includes('@')) return setMessage(message, 'Nhập email hợp lệ.', 'error');
      if (!/^\d{6}$/.test(token)) return setMessage(message, 'Nhập đúng mã OTP gồm 6 chữ số.', 'error');
      const client = getClient();
      if (!client) return setMessage(message, 'Dịch vụ xác thực chưa sẵn sàng.', 'error');
      const submit = form.querySelector('button[type="submit"]');
      submit.disabled = true;
      const label = submit.textContent;
      submit.textContent = 'Đang xác minh…';
      try {
        const { data, error } = await client.auth.verifyOtp({ email, token, type: 'email' });
        if (error || !data?.session) throw error || new Error('missing session');
        clearDeadline(LOGIN_OTP_DEADLINE_KEY);
        try { sessionStorage.removeItem(LOGIN_VERIFY_EMAIL_KEY); } catch (_) {}
        setMessage(message, 'Xác minh thành công. Đang mở tài khoản…', 'success');
        location.href = new URL('tai-khoan/?verified=1', document.baseURI).toString();
      } catch (_) {
        submit.disabled = false;
        submit.textContent = label;
        setMessage(message, 'OTP không đúng hoặc đã hết hạn. Hãy kiểm tra lại hoặc gửi mã mới.', 'error');
      }
    });
  }

  function translateAccountLabels() {
    const tier = document.querySelector('[data-account-tier]');
    const status = document.querySelector('[data-account-status]');
    const tierMap = { FREE: 'MIỄN PHÍ', TRIAL: 'DÙNG THỬ', PAID: 'TRẢ PHÍ' };
    const statusMap = { PENDING: 'CHỜ XÁC MINH', ACTIVE: 'ĐANG HOẠT ĐỘNG', SUSPENDED: 'TẠM KHÓA', DELETED: 'ĐÃ XÓA' };
    const render = () => {
      if (tier && tierMap[tier.textContent.trim()]) tier.textContent = tierMap[tier.textContent.trim()];
      if (status && statusMap[status.textContent.trim()]) status.textContent = statusMap[status.textContent.trim()];
    };
    render();
    if (tier || status) {
      const observer = new MutationObserver(render);
      if (tier) observer.observe(tier, { childList: true, characterData: true, subtree: true });
      if (status) observer.observe(status, { childList: true, characterData: true, subtree: true });
    }
  }

  function wireDeleteAccount() {
    const form = document.querySelector('[data-delete-account-form]');
    if (!form) return;
    const message = form.querySelector('[data-auth-message]');
    const input = form.elements.confirm_delete;
    const button = form.querySelector('button[type="submit"]');

    const updateButton = () => {
      if (button) button.disabled = String(input?.value || '').trim().toUpperCase() !== 'XOA';
    };
    input?.addEventListener('input', updateButton);
    updateButton();

    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (String(input?.value || '').trim().toUpperCase() !== 'XOA') {
        return setMessage(message, 'Nhập XOA để xác nhận xóa tài khoản.', 'error');
      }
      const client = getClient();
      if (!client) return setMessage(message, 'Phiên xác thực chưa sẵn sàng.', 'error');
      if (!confirm('Xóa vĩnh viễn tài khoản StockRadar và dữ liệu hồ sơ liên quan?')) return;

      button.disabled = true;
      const original = button.textContent;
      button.textContent = 'Đang xóa…';
      setMessage(message, 'Đang xác thực và xóa tài khoản…');
      try {
        const { data, error } = await client.functions.invoke('delete-account', {
          body: { confirm: 'DELETE_ACCOUNT' },
        });
        if (error || data?.status !== 'deleted') throw error || new Error('delete failed');
        try { await client.auth.signOut({ scope: 'local' }); } catch (_) {}
        try {
          for (const key of ['sr_pending_signup_email', SIGNUP_OTP_DEADLINE_KEY, LOGIN_OTP_DEADLINE_KEY, LOGIN_VERIFY_EMAIL_KEY]) sessionStorage.removeItem(key);
          localStorage.removeItem('stockradar-auth');
        } catch (_) {}
        location.href = new URL('?account_deleted=1', document.baseURI).toString();
      } catch (_) {
        button.disabled = false;
        button.textContent = original;
        setMessage(message, 'Chưa thể xóa tài khoản. Hãy đăng nhập lại rồi thử lại.', 'error');
      }
    });
  }

  function showAccountDeletedNotice() {
    const params = new URLSearchParams(location.search);
    if (params.get('account_deleted') !== '1') return;
    const main = document.querySelector('main');
    if (!main) return;
    const notice = document.createElement('div');
    notice.className = 'container account-deleted-banner';
    notice.setAttribute('role', 'status');
    notice.textContent = 'Tài khoản StockRadar đã được xóa.';
    main.prepend(notice);
  }

  document.addEventListener('DOMContentLoaded', () => {
    wirePersistentSignupOtpCooldown();
    wireMaskedOtpEmail();
    wireLoginOtpVerification();
    translateAccountLabels();
    wireDeleteAccount();
    showAccountDeletedNotice();
  });
})();
