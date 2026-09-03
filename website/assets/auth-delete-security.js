(() => {
  'use strict';

  function setMessage(target, message, kind = '') {
    if (!target) return;
    target.className = `auth-message${kind ? ` ${kind}` : ''}`;
    target.textContent = message;
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

  function wireDeleteReauthentication() {
    const form = document.querySelector('[data-delete-account-form][data-delete-account-reauth]');
    if (!form) return;

    const passwordInput = form.elements.delete_current_password;
    const confirmInput = form.elements.confirm_delete;
    const button = form.querySelector('button[type="submit"]');
    const message = form.querySelector('[data-auth-message]');

    const updateButton = () => {
      const confirmed = String(confirmInput?.value || '').trim().toUpperCase() === 'XOA';
      const hasPassword = String(passwordInput?.value || '').length >= 8;
      if (button) button.disabled = !(confirmed && hasPassword);
    };
    passwordInput?.addEventListener('input', updateButton);
    confirmInput?.addEventListener('input', updateButton);
    updateButton();

    form.addEventListener('submit', async event => {
      event.preventDefault();
      event.stopImmediatePropagation();

      const password = String(passwordInput?.value || '');
      const confirmed = String(confirmInput?.value || '').trim().toUpperCase() === 'XOA';
      if (!confirmed) return setMessage(message, 'Nhập XOA để xác nhận xóa tài khoản.', 'error');
      if (password.length < 8) return setMessage(message, 'Nhập mật khẩu hiện tại để xác minh lại danh tính.', 'error');

      const client = getClient();
      if (!client) return setMessage(message, 'Dịch vụ xác thực chưa sẵn sàng.', 'error');
      if (!confirm('Xóa vĩnh viễn tài khoản StockRadar và dữ liệu hồ sơ liên quan?')) return;

      const original = button?.textContent || 'Xóa tài khoản vĩnh viễn';
      if (button) {
        button.disabled = true;
        button.textContent = 'Đang xác minh…';
      }
      setMessage(message, 'Đang xác minh lại danh tính…');

      try {
        const { data: userData, error: userError } = await client.auth.getUser();
        const email = userData?.user?.email;
        if (userError || !email) throw new Error('missing user');

        const { error: reauthError } = await client.auth.signInWithPassword({ email, password });
        if (reauthError) throw new Error('reauth failed');

        if (button) button.textContent = 'Đang xóa…';
        setMessage(message, 'Đã xác minh. Đang xóa tài khoản…');
        const { data, error } = await client.functions.invoke('delete-account', {
          body: { confirm: 'DELETE_ACCOUNT' },
        });
        if (error || data?.status !== 'deleted') throw new Error('delete failed');

        try { await client.auth.signOut({ scope: 'local' }); } catch (_) {}
        try {
          sessionStorage.clear();
          localStorage.removeItem('stockradar-auth');
        } catch (_) {}
        location.href = new URL('?account_deleted=1', document.baseURI).toString();
      } catch (error) {
        const raw = String(error?.message || '');
        if (raw.includes('reauth')) {
          setMessage(message, 'Mật khẩu hiện tại không đúng.', 'error');
        } else if (raw.includes('missing user')) {
          setMessage(message, 'Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại.', 'error');
        } else {
          setMessage(message, 'Chưa thể xóa tài khoản. Hãy thử lại sau khi đăng nhập lại.', 'error');
        }
        if (button) {
          button.disabled = false;
          button.textContent = original;
        }
      } finally {
        if (passwordInput) passwordInput.value = '';
        updateButton();
      }
    }, { capture: true });
  }

  document.addEventListener('DOMContentLoaded', wireDeleteReauthentication);
})();
