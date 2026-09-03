(() => {
  'use strict';

  function isAuthRouteLink(link) {
    const href = String(link.getAttribute('href') || '').toLowerCase();
    return /(?:^|\/)dang-(?:ky|nhap)\/?(?:[?#].*)?$/.test(href);
  }

  function normalizeHeader() {
    const header = document.querySelector('.site-header');
    if (!header) return;

    const authGroup = header.querySelector('[data-header-auth-actions]');
    const menu = header.querySelector('[data-nav-menu]');

    if (menu) {
      menu.querySelectorAll('a').forEach(link => {
        if (!isAuthRouteLink(link)) return;
        link.hidden = true;
        link.setAttribute('aria-hidden', 'true');
        link.setAttribute('tabindex', '-1');
        link.dataset.headerAuthDuplicate = '1';
      });
    }

    header.querySelectorAll('a').forEach(link => {
      if (link.closest('[data-header-auth-actions]')) return;
      if (!isAuthRouteLink(link)) return;
      if (link.closest('[data-nav-menu]')) return;
      link.hidden = true;
      link.setAttribute('aria-hidden', 'true');
      link.setAttribute('tabindex', '-1');
      link.dataset.headerAuthDuplicate = '1';
    });

    if (authGroup) {
      authGroup.hidden = false;
      authGroup.removeAttribute('aria-hidden');
      const login = authGroup.querySelector('.header-login-cta');
      const register = authGroup.querySelector('.header-register-cta');
      if (login) {
        login.hidden = false;
        login.removeAttribute('aria-hidden');
        login.removeAttribute('tabindex');
      }
      if (register) {
        register.hidden = false;
        register.removeAttribute('aria-hidden');
        register.removeAttribute('tabindex');
      }
    }
  }

  let scheduled = false;
  function scheduleNormalize() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      normalizeHeader();
      scheduled = false;
    });
  }

  function boot() {
    normalizeHeader();
    const header = document.querySelector('.site-header');
    if (!header) return;
    const observer = new MutationObserver(scheduleNormalize);
    observer.observe(header, { childList: true, subtree: true, attributes: true, attributeFilter: ['href', 'class', 'hidden'] });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
