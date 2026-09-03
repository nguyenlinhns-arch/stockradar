(() => {
  'use strict';

  const OTP_RESEND_DEADLINE_KEY = 'sr_otp_resend_deadline';
  const OTP_RESEND_SECONDS = 60;

  function setMessage(target, message, kind = '') {
    if (!target) return;
    target.className = `auth-message${kind ? ` ${kind}` : ''}`;
    target.textContent = message;
  }

  function resendDeadline() {
    try { return Number(sessionStorage.getItem(OTP_RESEND_DEADLINE_KEY) || 0); } catch (_) { return 0; }
  }

  function setResendDeadline(seconds = OTP_RESEND_SECONDS) {
    const deadline = Date.now() + seconds * 1000;
    try { sessionStorage.setItem(OTP_RESEND_DEADLINE_KEY, String(deadline)); } catch (_) {}
    return deadline;
  }

  function remainingSeconds() {
    return Math.max(0, Math.ceil((resendDeadline() - Date.now()) / 1000));
  }

  function runPersistentCooldown(button) {
    if (!button) return;
    if (!button.dataset.defaultLabel) button.dataset.defaultLabel = button.textContent.trim();
    if (button._srPersistentOtpTimer) clearInterval(button._srPersistentOtpTimer);
    const render = () => {
      const left = remainingSeconds();
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
    if (remainingSeconds() > 0) button._srPersistentOtpTimer = setInterval(render, 1000);
  }

  function wirePersistentOtpCooldown() {
    const panel = document.querySelector('[data-auth-signup-otp-form]');
    const resend = panel?.querySelector('[data-auth-otp-resend]');
    if (!panel || !resend) return;

    runPersistentCooldown(resend);
    resend.addEventListener('click', () => {
      setResendDeadline();
      runPersistentCooldown(resend);
    }, { capture: true });

    const observer = new MutationObserver(() => {
      if (!panel.hidden) {
        if (remainingSeconds() <= 0) setResendDeadline();
        runPersistentCooldown(resend);
      }
    });
    observer.observe(panel, { attributes: true, attributeFilter: ['hidden'] });
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
      const client = window.StockRadarAuthClient;
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
          sessionStorage.clear();
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

  document.addEventListener('DOMContentLoaded', () => {
    wirePersistentOtpCooldown();
    translateAccountLabels();
    wireDeleteAccount();
  });
})();
