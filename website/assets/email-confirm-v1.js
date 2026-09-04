(() => {
  'use strict';

  const config = window.STOCKRADAR_AUTH_CONFIG || {};

  function setStatus(message, kind = '') {
    const target = document.querySelector('[data-email-confirm-status]');
    if (!target) return;
    target.className = `auth-message${kind ? ` ${kind}` : ''}`;
    target.textContent = message;
  }

  function destination() {
    const plan = new URLSearchParams(location.search).get('plan') === 'premium' ? 'premium' : 'free';
    return new URL(plan === 'premium' ? 'thanh-toan/?plan=premium' : 'tai-khoan/?verified=1', document.baseURI).toString();
  }

  async function init() {
    if (!config.configured || !config.supabaseUrl || !config.supabasePublishableKey || !window.supabase?.createClient) {
      setStatus('Dịch vụ xác minh tài khoản chưa sẵn sàng.', 'error');
      return;
    }

    const client = window.supabase.createClient(
      String(config.supabaseUrl).replace(/\/$/, ''),
      String(config.supabasePublishableKey),
      { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, storageKey: 'stockradar-auth' } },
    );

    let redirected = false;
    const finish = async session => {
      if (redirected || !session?.user?.email_confirmed_at) return false;
      redirected = true;
      try {
        sessionStorage.removeItem('sr_pending_signup_email');
        sessionStorage.removeItem('sr_pending_signup_plan');
        sessionStorage.removeItem('sr_pending_signup_next');
      } catch (_) {}
      setStatus('Email đã được xác minh. Đang tiếp tục…', 'success');
      window.location.replace(destination());
      return true;
    };

    const { data } = await client.auth.getSession();
    if (await finish(data?.session)) return;

    const { data: subscription } = client.auth.onAuthStateChange(async (_event, session) => {
      if (await finish(session)) subscription?.subscription?.unsubscribe?.();
    });

    setTimeout(async () => {
      if (redirected) return;
      const { data: latest } = await client.auth.getSession();
      if (await finish(latest?.session)) return;
      setStatus('Liên kết xác minh không hợp lệ hoặc đã hết hạn. Hãy quay lại trang đăng ký để tạo liên kết mới.', 'error');
      document.querySelector('[data-email-confirm-actions]')?.removeAttribute('hidden');
    }, 4500);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
