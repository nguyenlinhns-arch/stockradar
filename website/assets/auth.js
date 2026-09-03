(() => {
  'use strict';

  const config = window.STOCKRADAR_AUTH_CONFIG || {};
  const providerReady = Boolean(
    config.configured &&
    config.provider === 'supabase' &&
    config.supabaseUrl &&
    config.supabasePublishableKey &&
    window.supabase &&
    typeof window.supabase.createClient === 'function'
  );

  let authClient = null;

  function siteUrl(path = '') {
    return new URL(String(path).replace(/^\/+/, ''), document.baseURI).toString();
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[character]));
  }

  function setMessage(target, message, kind = '') {
    if (!target) return;
    target.className = `auth-message${kind ? ` ${kind}` : ''}`;
    target.textContent = message;
  }

  function setBusy(form, busy, label = 'Đang xử lý…') {
    if (!form) return;
    const button = form.querySelector('button[type="submit"]');
    if (!button) return;
    if (!button.dataset.defaultLabel) button.dataset.defaultLabel = button.textContent.trim();
    button.disabled = busy;
    button.textContent = busy ? label : button.dataset.defaultLabel;
  }

  function lockForm(form, message) {
    if (!form) return;
    form.querySelectorAll('input, button, select, textarea').forEach(control => { control.disabled = true; });
    setMessage(form.querySelector('[data-auth-message]'), message, 'error');
  }

  function normalizeEmail(value) {
    return String(value || '').trim().toLowerCase();
  }

  function passwordProblem(value) {
    const password = String(value || '');
    if (password.length < 8) return 'Mật khẩu cần ít nhất 8 ký tự.';
    if (password.length > 128) return 'Mật khẩu tối đa 128 ký tự.';
    return '';
  }

  function friendlyError(error) {
    const raw = String(error?.message || '').toLowerCase();
    if (raw.includes('invalid login credentials')) return 'Email hoặc mật khẩu không đúng.';
    if (raw.includes('email not confirmed')) return 'Email chưa được xác minh. Hãy kiểm tra hộp thư rồi thử lại.';
    if (raw.includes('user already registered') || raw.includes('already been registered')) return 'Email này đã được đăng ký. Hãy đăng nhập hoặc dùng chức năng quên mật khẩu.';
    if (raw.includes('rate limit') || raw.includes('too many')) return 'Có quá nhiều yêu cầu. Vui lòng thử lại sau.';
    if (raw.includes('password')) return 'Mật khẩu chưa đạt yêu cầu bảo mật.';
    return 'Không thể hoàn tất yêu cầu. Vui lòng thử lại.';
  }

  function safeNext(value) {
    if (!value) return siteUrl('tai-khoan/');
    try {
      const target = new URL(value, location.href);
      if (target.origin !== location.origin) return siteUrl('tai-khoan/');
      const base = new URL(document.baseURI);
      if (!target.pathname.startsWith(base.pathname)) return siteUrl('tai-khoan/');
      return target.toString();
    } catch (_) {
      return siteUrl('tai-khoan/');
    }
  }

  function passwordToggles() {
    document.querySelectorAll('[data-password-toggle]').forEach(button => {
      button.addEventListener('click', () => {
        const input = document.getElementById(button.dataset.passwordToggle);
        if (!input) return;
        const showing = input.type === 'text';
        input.type = showing ? 'password' : 'text';
        button.textContent = showing ? 'Hiện' : 'Ẩn';
        button.setAttribute('aria-pressed', String(!showing));
      });
    });
  }

  function navMarkup(user) {
    if (!user) {
      return `<a class="auth-nav-login" href="${siteUrl('dang-nhap/')}">Đăng nhập</a><a class="button button-primary button-small auth-nav-signup" href="${siteUrl('signup/')}">Đăng ký</a>`;
    }
    const email = escapeHtml(user.email || 'Tài khoản');
    const initial = escapeHtml((user.email || 'S').slice(0, 1).toUpperCase());
    return `<a class="auth-account-link" href="${siteUrl('tai-khoan/')}" title="${email}"><span class="auth-avatar">${initial}</span><span class="auth-account-email">${email}</span></a><button class="auth-logout" type="button" data-auth-logout>Đăng xuất</button>`;
  }

  async function currentUser() {
    if (!authClient) return null;
    const { data, error } = await authClient.auth.getUser();
    if (error) return null;
    return data?.user || null;
  }

  async function refreshNav() {
    const target = document.querySelector('[data-auth-nav]');
    if (!target) return;
    target.innerHTML = navMarkup(providerReady ? await currentUser() : null);
  }

  function mountNav() {
    const nav = document.querySelector('.site-header .nav');
    if (!nav || nav.querySelector('[data-auth-nav]')) return;
    const target = document.createElement('div');
    target.className = 'auth-nav';
    target.dataset.authNav = '';
    target.innerHTML = navMarkup(null);
    nav.append(target);
    target.addEventListener('click', async event => {
      const logout = event.target.closest('[data-auth-logout]');
      if (!logout || !authClient) return;
      logout.disabled = true;
      await authClient.auth.signOut();
      location.href = siteUrl('dang-nhap/?signed_out=1');
    });
  }

  function wireSignup() {
    const form = document.querySelector('[data-auth-signup-form]');
    if (!form) return;
    if (!providerReady) {
      lockForm(form, 'Đăng ký đang chờ kết nối dịch vụ xác thực. Website chưa nhận mật khẩu.');
      return;
    }
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const message = form.querySelector('[data-auth-message]');
      const email = normalizeEmail(form.elements.email?.value);
      const password = String(form.elements.password?.value || '');
      const confirm = String(form.elements.password_confirm?.value || '');
      const terms = Boolean(form.elements.terms?.checked);
      const problem = passwordProblem(password);
      if (!email || !email.includes('@')) return setMessage(message, 'Nhập email hợp lệ.', 'error');
      if (problem) return setMessage(message, problem, 'error');
      if (password !== confirm) return setMessage(message, 'Mật khẩu nhập lại chưa khớp.', 'error');
      if (!terms) return setMessage(message, 'Cần đồng ý Điều khoản và Chính sách quyền riêng tư để tạo tài khoản.', 'error');

      setBusy(form, true, 'Đang tạo tài khoản…');
      setMessage(message, 'Đang tạo tài khoản bảo mật…');
      try {
        const { data, error } = await authClient.auth.signUp({
          email,
          password,
          options: { emailRedirectTo: siteUrl('tai-khoan/?verified=1') }
        });
        if (error) throw error;
        form.elements.password.value = '';
        form.elements.password_confirm.value = '';
        if (data?.session) {
          setMessage(message, 'Tạo tài khoản thành công. Đang mở trang tài khoản…', 'success');
          location.href = siteUrl('tai-khoan/');
          return;
        }
        setMessage(message, 'Đã tạo tài khoản. Hãy mở email xác minh của StockRadar trước khi đăng nhập.', 'success');
      } catch (error) {
        setMessage(message, friendlyError(error), 'error');
      } finally {
        setBusy(form, false);
      }
    });
  }

  function wireLogin() {
    const form = document.querySelector('[data-auth-login-form]');
    if (!form) return;
    if (!providerReady) {
      lockForm(form, 'Đăng nhập đang chờ kết nối dịch vụ xác thực. Website chưa nhận mật khẩu.');
      return;
    }
    const params = new URLSearchParams(location.search);
    const presetEmail = normalizeEmail(params.get('email'));
    if (presetEmail && form.elements.email) form.elements.email.value = presetEmail;
    if (params.get('signed_out') === '1') setMessage(form.querySelector('[data-auth-message]'), 'Đã đăng xuất an toàn.', 'success');

    form.addEventListener('submit', async event => {
      event.preventDefault();
      const message = form.querySelector('[data-auth-message]');
      const email = normalizeEmail(form.elements.email?.value);
      const password = String(form.elements.password?.value || '');
      if (!email || !password) return setMessage(message, 'Nhập đầy đủ email và mật khẩu.', 'error');
      setBusy(form, true, 'Đang đăng nhập…');
      try {
        const { error } = await authClient.auth.signInWithPassword({ email, password });
        form.elements.password.value = '';
        if (error) throw error;
        setMessage(message, 'Đăng nhập thành công.', 'success');
        location.href = safeNext(params.get('next'));
      } catch (error) {
        form.elements.password.value = '';
        setMessage(message, friendlyError(error), 'error');
      } finally {
        setBusy(form, false);
      }
    });
  }

  function wireForgotPassword() {
    const form = document.querySelector('[data-auth-forgot-form]');
    if (!form) return;
    if (!providerReady) {
      lockForm(form, 'Khôi phục mật khẩu đang chờ kết nối dịch vụ xác thực.');
      return;
    }
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const message = form.querySelector('[data-auth-message]');
      const email = normalizeEmail(form.elements.email?.value);
      if (!email || !email.includes('@')) return setMessage(message, 'Nhập email hợp lệ.', 'error');
      setBusy(form, true, 'Đang gửi…');
      try {
        await authClient.auth.resetPasswordForEmail(email, { redirectTo: siteUrl('dat-lai-mat-khau/') });
        setMessage(message, 'Nếu email có tài khoản StockRadar, hướng dẫn đặt lại mật khẩu đã được gửi.', 'success');
      } catch (_) {
        setMessage(message, 'Nếu email có tài khoản StockRadar, hướng dẫn đặt lại mật khẩu đã được gửi.', 'success');
      } finally {
        setBusy(form, false);
      }
    });
  }

  function wirePasswordUpdate() {
    document.querySelectorAll('[data-auth-update-password-form]').forEach(form => {
      if (!providerReady) {
        lockForm(form, 'Đổi mật khẩu đang chờ kết nối dịch vụ xác thực.');
        return;
      }
      form.addEventListener('submit', async event => {
        event.preventDefault();
        const message = form.querySelector('[data-auth-message]');
        const password = String(form.elements.password?.value || '');
        const confirm = String(form.elements.password_confirm?.value || '');
        const problem = passwordProblem(password);
        if (problem) return setMessage(message, problem, 'error');
        if (password !== confirm) return setMessage(message, 'Mật khẩu nhập lại chưa khớp.', 'error');
        setBusy(form, true, 'Đang cập nhật…');
        try {
          const { data: sessionData } = await authClient.auth.getSession();
          if (!sessionData?.session) throw new Error('missing session');
          const { error } = await authClient.auth.updateUser({ password });
          if (error) throw error;
          form.reset();
          setMessage(message, 'Đã cập nhật mật khẩu.', 'success');
        } catch (error) {
          const missing = String(error?.message || '').includes('missing session');
          setMessage(message, missing ? 'Phiên đổi mật khẩu đã hết hạn. Hãy yêu cầu một liên kết mới.' : friendlyError(error), 'error');
        } finally {
          setBusy(form, false);
        }
      });
    });
  }

  function formatDate(value) {
    if (!value) return '—';
    try {
      return new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(value));
    } catch (_) {
      return '—';
    }
  }

  async function renderAccount() {
    const root = document.querySelector('[data-auth-account]');
    if (!root) return;
    const status = root.querySelector('[data-auth-account-status]');
    const details = root.querySelector('[data-auth-account-details]');
    const guest = root.querySelector('[data-auth-account-guest]');
    if (!providerReady) {
      if (details) details.hidden = true;
      if (guest) guest.hidden = false;
      setMessage(status, 'Dịch vụ xác thực chưa được kết nối với bản production.', 'error');
      return;
    }
    setMessage(status, 'Đang kiểm tra phiên đăng nhập…');
    const user = await currentUser();
    if (!user) {
      if (details) details.hidden = true;
      if (guest) guest.hidden = false;
      setMessage(status, 'Bạn chưa đăng nhập.', '');
      return;
    }
    if (guest) guest.hidden = true;
    if (details) details.hidden = false;
    const emailTarget = root.querySelector('[data-account-email]');
    const verifiedTarget = root.querySelector('[data-account-verified]');
    const createdTarget = root.querySelector('[data-account-created]');
    if (emailTarget) emailTarget.textContent = user.email || '—';
    if (verifiedTarget) verifiedTarget.textContent = user.email_confirmed_at ? 'Đã xác minh' : 'Chưa xác minh';
    if (createdTarget) createdTarget.textContent = formatDate(user.created_at);
    setMessage(status, 'Phiên đăng nhập đang hoạt động.', 'success');
  }

  async function init() {
    mountNav();
    passwordToggles();

    if (providerReady) {
      authClient = window.supabase.createClient(
        String(config.supabaseUrl).replace(/\/+$/, ''),
        String(config.supabasePublishableKey),
        {
          auth: {
            persistSession: true,
            autoRefreshToken: true,
            detectSessionInUrl: true,
            storageKey: 'stockradar-auth'
          }
        }
      );
      authClient.auth.onAuthStateChange(() => {
        refreshNav();
        renderAccount();
      });
    }

    wireSignup();
    wireLogin();
    wireForgotPassword();
    wirePasswordUpdate();
    await refreshNav();
    await renderAccount();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
