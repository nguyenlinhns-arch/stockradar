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

  function passwordProblem(value) {
    const password = String(value || '');
    if (password.length < 8) return 'Mật khẩu mới cần ít nhất 8 ký tự.';
    if (password.length > 128) return 'Mật khẩu mới tối đa 128 ký tự.';
    return '';
  }

  function wireCurrentPasswordRequirement() {
    const form = document.querySelector('[data-auth-update-password-form][data-require-current-password]');
    if (!form) return;

    form.addEventListener('submit', async event => {
      event.preventDefault();
      event.stopImmediatePropagation();

      const message = form.querySelector('[data-auth-message]');
      const currentPassword = String(form.elements.current_password?.value || '');
      const password = String(form.elements.password?.value || '');
      const confirm = String(form.elements.password_confirm?.value || '');
      const problem = passwordProblem(password);

      if (!currentPassword) return setMessage(message, 'Nhập mật khẩu hiện tại.', 'error');
      if (problem) return setMessage(message, problem, 'error');
      if (password !== confirm) return setMessage(message, 'Mật khẩu mới nhập lại chưa khớp.', 'error');
      if (password === currentPassword) return setMessage(message, 'Mật khẩu mới phải khác mật khẩu hiện tại.', 'error');

      const client = getClient();
      if (!client) return setMessage(message, 'Dịch vụ xác thực chưa sẵn sàng.', 'error');
      const button = form.querySelector('button[type="submit"]');
      const original = button?.textContent || 'Đổi mật khẩu';
      if (button) {
        button.disabled = true;
        button.textContent = 'Đang cập nhật…';
      }
      setMessage(message, 'Đang xác minh mật khẩu hiện tại…');

      try {
        const { data: sessionData } = await client.auth.getSession();
        if (!sessionData?.session) throw new Error('missing session');
        const { error } = await client.auth.updateUser({ password, currentPassword });
        if (error) throw error;
        form.reset();
        setMessage(message, 'Đã đổi mật khẩu an toàn.', 'success');
      } catch (error) {
        const raw = String(error?.message || '').toLowerCase();
        if (raw.includes('current') && raw.includes('password')) {
          setMessage(message, 'Mật khẩu hiện tại không đúng.', 'error');
        } else if (raw.includes('missing session') || raw.includes('session')) {
          setMessage(message, 'Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại.', 'error');
        } else {
          setMessage(message, 'Chưa thể đổi mật khẩu. Kiểm tra mật khẩu hiện tại rồi thử lại.', 'error');
        }
      } finally {
        form.elements.current_password.value = '';
        form.elements.password.value = '';
        form.elements.password_confirm.value = '';
        if (button) {
          button.disabled = false;
          button.textContent = original;
        }
      }
    }, { capture: true });
  }

  document.addEventListener('DOMContentLoaded', wireCurrentPasswordRequirement);
})();
