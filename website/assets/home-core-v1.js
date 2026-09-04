(() => {
  'use strict';

  const DIRECT_SIGNUP_ROUTE = 'signup/';
  const CONSENT_VERSION = '2026-09-03';
  const FALLBACK_SUPABASE_URL = 'https://xamviatbxufjlpiwhebb.supabase.co';

  function emailDeliveryReady() {
    return window.STOCKRADAR_AUTH_CONFIG?.emailDeliveryReady === true;
  }

  function normalizeTicker(value) {
    return String(value || '').trim().toUpperCase().replace(/[^A-Z]/g, '').slice(0, 3);
  }

  function validTicker(value) {
    return /^[A-Z]{3}$/.test(value);
  }

  function validEmail(value) {
    return /^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$/i.test(String(value || '').trim());
  }

  function stockUrl(ticker) {
    return new URL(`co-phieu/?ticker=${encodeURIComponent(ticker)}`, document.baseURI).href;
  }

  function registrationUrl() {
    return new URL('dang-ky/', document.baseURI).href;
  }

  function leadUrl() {
    return new URL('nhan-ban-tin/', document.baseURI).href;
  }

  function premiumUrl() {
    return new URL('thanh-toan/?plan=premium', document.baseURI).href;
  }

  function directSignupUrl() {
    return new URL(DIRECT_SIGNUP_ROUTE, document.baseURI).href;
  }

  function emailInterestEndpoint() {
    const base = window.STOCKRADAR_AUTH_CONFIG?.supabaseUrl || FALLBACK_SUPABASE_URL;
    return `${String(base).replace(/\/$/, '')}/functions/v1/email-interest`;
  }

  function setSearchMessage(form, message, kind = '') {
    const target = form?.parentElement?.querySelector('[data-stock-search-result]');
    if (!target) return;
    target.className = `search-result${kind ? ` ${kind}` : ''}`;
    target.textContent = message;
  }

  function mountNavigation() {
    const toggle = document.querySelector('[data-nav-toggle]');
    const menu = document.querySelector('[data-nav-menu]');
    if (!toggle || !menu) return;

    const close = () => {
      menu.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
    };
    const open = () => {
      menu.classList.add('is-open');
      toggle.setAttribute('aria-expanded', 'true');
    };

    toggle.addEventListener('click', event => {
      event.stopPropagation();
      menu.classList.contains('is-open') ? close() : open();
    });
    document.addEventListener('click', event => {
      if (!menu.contains(event.target) && !toggle.contains(event.target)) close();
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') close();
    });
    menu.addEventListener('click', event => {
      if (event.target.closest('a')) close();
    });
  }

  function mountTickerSearch() {
    document.querySelectorAll('[data-stock-search-form]').forEach(form => {
      const input = form.querySelector('input[name="ticker"]');
      if (!input) return;
      input.addEventListener('input', () => {
        const normalized = normalizeTicker(input.value);
        if (input.value !== normalized) input.value = normalized;
        setSearchMessage(form, '');
      });
      form.addEventListener('submit', event => {
        event.preventDefault();
        const ticker = normalizeTicker(input.value);
        input.value = ticker;
        if (!validTicker(ticker)) {
          setSearchMessage(form, 'Nhập mã gồm đúng 3 chữ cái, ví dụ FPT.', 'error');
          input.focus();
          return;
        }
        window.location.assign(stockUrl(ticker));
      });
    });
  }

  function setLeadMessage(form, message, kind = '') {
    const target = form?.querySelector('[data-home-lead-message]');
    if (!target) return;
    target.className = `home-lead-message${kind ? ` ${kind}` : ''}`;
    target.textContent = message;
  }

  function removeLeadNext(form) {
    form.querySelector('[data-home-lead-next]')?.remove();
  }

  function renderLeadNext(form, email) {
    removeLeadNext(form);
    const url = new URL(emailDeliveryReady() ? directSignupUrl() : registrationUrl());
    if (emailDeliveryReady()) {
      url.searchParams.set('plan', 'free');
      url.searchParams.set('email', email);
    }
    const link = document.createElement('a');
    link.className = 'home-lead-next';
    link.dataset.homeLeadNext = '';
    link.href = url.toString();
    link.textContent = emailDeliveryReady()
      ? 'Tạo tài khoản Free để kích hoạt bản tin'
      : 'Xem gói Free / Premium';
    form.append(link);
  }

  function mountEmailLead() {
    const form = document.querySelector('[data-home-email-form]');
    if (!form) return;
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const email = String(form.elements.email?.value || '').trim().toLowerCase();
      const dailyBrief = Boolean(form.elements.daily_brief?.checked);
      const privacyAccepted = Boolean(form.elements.privacy?.checked);
      const company = String(form.elements.company?.value || '');
      const button = form.querySelector('button[type="submit"]');

      removeLeadNext(form);
      if (!validEmail(email)) {
        setLeadMessage(form, 'Nhập email hợp lệ để đăng ký bản rà soát 09:00.', 'error');
        form.elements.email?.focus();
        return;
      }
      if (!dailyBrief) {
        setLeadMessage(form, 'Chọn xác nhận muốn nhận bản rà soát 09:00.', 'error');
        return;
      }
      if (!privacyAccepted) {
        setLeadMessage(form, 'Cần đồng ý Chính sách quyền riêng tư trước khi tiếp tục.', 'error');
        return;
      }

      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 10000);
      if (button) button.disabled = true;
      setLeadMessage(form, 'Đang ghi nhận email…');
      try {
        const response = await fetch(emailInterestEndpoint(), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email,
            daily_brief: true,
            event_alerts: false,
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
          throw new Error(payload.message || 'Chưa thể ghi nhận email lúc này.');
        }
        try { localStorage.setItem('sr_email_lead_captured', '1'); } catch (_) {}
        setLeadMessage(form, 'Đã ghi nhận email. Hoàn tất tạo tài khoản Free và xác minh email để kích hoạt bản tin 09:00.', 'success');
        renderLeadNext(form, email);
        form.elements.daily_brief.checked = false;
        form.elements.privacy.checked = false;
      } catch (error) {
        const message = error?.name === 'AbortError'
          ? 'Kết nối quá thời gian. Vui lòng thử lại.'
          : String(error?.message || 'Chưa thể ghi nhận email lúc này.');
        setLeadMessage(form, message, 'error');
      } finally {
        clearTimeout(timeout);
        if (button) button.disabled = false;
      }
    });
  }

  function mountRegistration() {
    const compareHref = registrationUrl();
    const freeLeadHref = leadUrl();

    document.querySelectorAll('.header-register-cta').forEach(link => {
      link.href = freeLeadHref;
      link.textContent = 'Nhận email 09:00';
      link.setAttribute('aria-label', 'Đăng ký nhận bản rà soát StockRadar lúc 09:00 miễn phí');
    });

    document.querySelectorAll('a[href="signup/"]').forEach(link => {
      if (link.closest('[data-email-conversion]')) return;
      link.href = compareHref;
    });

    const mobile = document.querySelector('.mobile-newsletter-bar a');
    if (mobile) {
      mobile.href = '#nhan-ban-tin';
      mobile.textContent = 'Nhận email 09:00';
    }

    emailDeliveryReady();
    directSignupUrl();
    premiumUrl();
  }

  function mount() {
    mountNavigation();
    mountTickerSearch();
    mountEmailLead();
    mountRegistration();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();