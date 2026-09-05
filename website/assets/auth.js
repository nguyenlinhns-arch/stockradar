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
  const PENDING_SIGNUP_KEY = 'sr_pending_signup_email';
  const PENDING_SIGNUP_PLAN_KEY = 'sr_pending_signup_plan';
  const PENDING_SIGNUP_NEXT_KEY = 'sr_pending_signup_next';
  const OTP_RESEND_SECONDS = 60;

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

  function normalizeOtp(value) {
    return String(value || '').replace(/\D/g, '').slice(0, 6);
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
    if (raw.includes('email not confirmed')) return 'Email chưa được xác minh. Hãy nhập OTP 6 số hoặc kiểm tra email xác minh.';
    if (raw.includes('user already registered') || raw.includes('already been registered')) return 'Email này đã được đăng ký. Hãy đăng nhập hoặc dùng chức năng quên mật khẩu.';
    if (raw.includes('token') && (raw.includes('expired') || raw.includes('invalid'))) return 'Mã OTP không đúng hoặc đã hết hạn. Hãy kiểm tra lại hoặc gửi mã mới.';
    if (raw.includes('otp') && raw.includes('expired')) return 'Mã OTP đã hết hạn. Hãy gửi mã mới.';
    if (raw.includes('rate limit') || raw.includes('too many')) return 'Có quá nhiều yêu cầu. Vui lòng thử lại sau.';
    if (raw.includes('password')) return 'Mật khẩu chưa đạt yêu cầu bảo mật.';
    return 'Không thể hoàn tất yêu cầu. Vui lòng thử lại.';
  }

  function safeNext(value) {
    if (!value) return siteUrl('./');
    try {
      const target = new URL(value, document.baseURI);
      if (target.origin !== location.origin) return siteUrl('./');
      const base = new URL(document.baseURI);
      if (!target.pathname.startsWith(base.pathname)) return siteUrl('./');
      return target.toString();
    } catch (_) {
      return siteUrl('./');
    }
  }

  function pendingSignupEmail() {
    try { return normalizeEmail(sessionStorage.getItem(PENDING_SIGNUP_KEY)); } catch (_) { return ''; }
  }

  function setPendingSignupEmail(email) {
    try { sessionStorage.setItem(PENDING_SIGNUP_KEY, normalizeEmail(email)); } catch (_) {}
  }

  function clearPendingSignupEmail() {
    try { sessionStorage.removeItem(PENDING_SIGNUP_KEY); } catch (_) {}
  }

  function selectedSignupPlan(form) {
    return String(form?.elements?.selected_plan?.value || 'free').trim().toLowerCase() === 'premium' ? 'premium' : 'free';
  }

  function signupDestination(plan) {
    const params = new URLSearchParams(location.search);
    const requestedNext = params.get('next');
    if (requestedNext) return safeNext(requestedNext);
    const target = new URL(plan === 'premium' ? 'thanh-toan/?plan=premium' : 'tai-khoan/', document.baseURI);
    const ticker = String(params.get('ticker') || '').trim().toUpperCase();
    if (/^[A-Z0-9]{3}$/.test(ticker)) target.searchParams.set('ticker', ticker);
    return target.toString();
  }

  function setPendingSignupFlow(plan, destination) {
    try {
      sessionStorage.setItem(PENDING_SIGNUP_PLAN_KEY, plan === 'premium' ? 'premium' : 'free');
      sessionStorage.setItem(PENDING_SIGNUP_NEXT_KEY, destination);
    } catch (_) {}
  }

  function pendingSignupDestination() {
    try {
      const saved = sessionStorage.getItem(PENDING_SIGNUP_NEXT_KEY) || '';
      if (saved) return safeNext(saved);
      const plan = sessionStorage.getItem(PENDING_SIGNUP_PLAN_KEY) === 'premium' ? 'premium' : 'free';
      return signupDestination(plan);
    } catch (_) {
      return signupDestination('free');
    }
  }

  function clearPendingSignupFlow() {
    try {
      sessionStorage.removeItem(PENDING_SIGNUP_PLAN_KEY);
      sessionStorage.removeItem(PENDING_SIGNUP_NEXT_KEY);
    } catch (_) {}
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

  function startOtpCooldown(button, seconds = OTP_RESEND_SECONDS) {
    if (!button) return;
    if (button._srOtpTimer) clearInterval(button._srOtpTimer);
    if (!button.dataset.defaultLabel) button.dataset.defaultLabel = button.textContent.trim();
    let left = seconds;
    button.disabled = true;
    button.textContent = `Gửi lại sau ${left}s`;
    button._srOtpTimer = setInterval(() => {
      left -= 1;
      if (left <= 0) {
        clearInterval(button._srOtpTimer);
        button._srOtpTimer = null;
        button.disabled = false;
        button.textContent = button.dataset.defaultLabel;
        return;
      }
      button.textContent = `Gửi lại sau ${left}s`;
    }, 1000);
  }

  function showOtpStep(signupForm, otpForm, email, { cooldown = false } = {}) {
    if (!signupForm || !otpForm) return;
    const normalized = normalizeEmail(email);
    if (!normalized) return;
    setPendingSignupEmail(normalized);
    signupForm.hidden = true;
    otpForm.hidden = false;
    const emailTarget = otpForm.querySelector('[data-auth-otp-email]');
    if (emailTarget) emailTarget.textContent = normalized;
    const otpInput = otpForm.elements.otp;
    if (otpInput) {
      otpInput.value = '';
      setTimeout(() => otpInput.focus(), 0);
    }
    if (cooldown) startOtpCooldown(otpForm.querySelector('[data-auth-otp-resend]'));
  }

  function showSignupStep(signupForm, otpForm, email = '') {
    if (!signupForm || !otpForm) return;
    clearPendingSignupEmail();
    otpForm.hidden = true;
    signupForm.hidden = false;
    if (signupForm.elements.email && email) signupForm.elements.email.value = normalizeEmail(email);
    setTimeout(() => signupForm.elements.email?.focus(), 0);
  }

  function wireSignup() {
    const form = document.querySelector('[data-auth-signup-form]');
    const otpForm = document.querySelector('[data-auth-signup-otp-form]');
    if (!form) return;
    if (!providerReady) {
      lockForm(form, 'Đăng ký đang chờ kết nối dịch vụ xác thực. Website chưa nhận mật khẩu.');
      if (otpForm) lockForm(otpForm, 'Xác minh OTP đang chờ kết nối dịch vụ xác thực.');
      return;
    }

    if (otpForm) {
      const existing = pendingSignupEmail();
      if (existing) showOtpStep(form, otpForm, existing);

      otpForm.elements.otp?.addEventListener('input', event => {
        event.target.value = normalizeOtp(event.target.value);
      });

      otpForm.addEventListener('submit', async event => {
        event.preventDefault();
        const message = otpForm.querySelector('[data-auth-message]');
        const email = pendingSignupEmail();
        const token = normalizeOtp(otpForm.elements.otp?.value);
        if (!email) return showSignupStep(form, otpForm);
        if (!/^\d{6}$/.test(token)) return setMessage(message, 'Nhập đúng mã OTP gồm 6 chữ số.', 'error');
        setBusy(otpForm, true, 'Đang xác minh…');
        try {
          const { data, error } = await authClient.auth.verifyOtp({ email, token, type: 'email' });
          if (error) throw error;
          if (!data?.session) throw new Error('missing verified session');
          const destination = pendingSignupDestination();
          clearPendingSignupEmail();
          clearPendingSignupFlow();
          setMessage(message, 'Xác minh thành công. Đang tiếp tục…', 'success');
          location.href = destination;
        } catch (error) {
          setMessage(message, friendlyError(error), 'error');
        } finally {
          setBusy(otpForm, false);
        }
      });

      otpForm.querySelector('[data-auth-otp-resend]')?.addEventListener('click', async event => {
        const button = event.currentTarget;
        const message = otpForm.querySelector('[data-auth-message]');
        const email = pendingSignupEmail();
        if (!email) return showSignupStep(form, otpForm);
        button.disabled = true;
        try {
          const { error } = await authClient.auth.resend({
            type: 'signup',
            email,
            options: { emailRedirectTo: pendingSignupDestination() }
          });
          if (error) throw error;
          setMessage(message, 'Đã gửi lại mã xác minh. Kiểm tra cả Inbox và Spam.', 'success');
          startOtpCooldown(button);
        } catch (error) {
          button.disabled = false;
          setMessage(message, friendlyError(error), 'error');
        }
      });

      otpForm.querySelector('[data-auth-otp-change]')?.addEventListener('click', () => {
        const email = pendingSignupEmail();
        showSignupStep(form, otpForm, email);
      });
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

      const plan = selectedSignupPlan(form);
      const destination = signupDestination(plan);
      setPendingSignupFlow(plan, destination);

      setBusy(form, true, 'Đang tạo tài khoản…');
      setMessage(message, 'Đang tạo tài khoản và gửi mã xác minh…');
      try {
        const { data, error } = await authClient.auth.signUp({
          email,
          password,
          options: { emailRedirectTo: destination }
        });
        form.elements.password.value = '';
        form.elements.password_confirm.value = '';
        if (error) throw error;
        if (data?.session) {
          clearPendingSignupEmail();
          clearPendingSignupFlow();
          setMessage(message, plan === 'premium' ? 'Tạo tài khoản thành công. Đang mở thanh toán Premium…' : 'Tạo tài khoản thành công. Đang mở trang tài khoản…', 'success');
          location.href = destination;
          return;
        }
        if (otpForm) {
          showOtpStep(form, otpForm, email, { cooldown: true });
          setMessage(otpForm.querySelector('[data-auth-message]'), 'Mã xác minh đã được gửi. Nhập OTP 6 số từ email StockRadar.', 'success');
        } else {
          setMessage(message, 'Đã tạo tài khoản. Kiểm tra email để xác minh.', 'success');
        }
      } catch (error) {
        form.elements.password.value = '';
        form.elements.password_confirm.value = '';
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
        clearPendingSignupEmail();
        clearPendingSignupFlow();
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

  async function accountProfile(userId) {
    if (!authClient || !userId) return null;
    const { data, error } = await authClient
      .from('profiles')
      .select('account_tier,account_status,created_at')
      .eq('id', userId)
      .maybeSingle();
    if (error) return null;
    return data || null;
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
    if (user.email_confirmed_at) clearPendingSignupEmail();
    if (guest) guest.hidden = true;
    if (details) details.hidden = false;
    const profile = await accountProfile(user.id);
    const emailTarget = root.querySelector('[data-account-email]');
    const verifiedTarget = root.querySelector('[data-account-verified]');
    const createdTarget = root.querySelector('[data-account-created]');
    const tierTarget = root.querySelector('[data-account-tier]');
    const accountStatusTarget = root.querySelector('[data-account-status]');
    if (emailTarget) emailTarget.textContent = user.email || '—';
    if (verifiedTarget) verifiedTarget.textContent = user.email_confirmed_at ? 'Đã xác minh' : 'Chưa xác minh';
    if (createdTarget) createdTarget.textContent = formatDate(profile?.created_at || user.created_at);
    if (tierTarget) tierTarget.textContent = profile?.account_tier || '—';
    if (accountStatusTarget) accountStatusTarget.textContent = profile?.account_status || '—';
    setMessage(status, profile ? 'Phiên đăng nhập và hồ sơ tài khoản đang hoạt động.' : 'Phiên đăng nhập đang hoạt động; hồ sơ tài khoản đang đồng bộ.', profile ? 'success' : '');
  }

  async function init() {
    mountNav();
    passwordToggles();

    if (providerReady) {
      authClient = window.StockRadarAuthClient || window.supabase.createClient(
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
      window.StockRadarAuthClient = authClient;
      authClient.auth.onAuthStateChange((_event, session) => {
        if (session?.user?.email_confirmed_at) clearPendingSignupEmail();
        // Supabase holds its session lock during this callback. Defer API calls.
        setTimeout(() => { refreshNav(); renderAccount(); }, 0);
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
