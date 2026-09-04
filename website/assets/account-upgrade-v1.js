(() => {
  'use strict';

  function premiumUrl() {
    return new URL('thanh-toan/?plan=premium', document.baseURI).toString();
  }

  function ensureCard(root) {
    let card = root.querySelector('[data-account-upgrade-card]');
    if (card) return card;
    card = document.createElement('section');
    card.className = 'account-upgrade-card';
    card.dataset.accountUpgradeCard = '';
    card.hidden = true;
    const grid = root.querySelector('.auth-account-grid');
    if (grid) grid.insertAdjacentElement('afterend', card);
    else root.prepend(card);
    return card;
  }

  function userTier(value) {
    const normalized = String(value || '').trim().toUpperCase();
    if (normalized === 'PAID' || normalized === 'TRIAL' || normalized === 'PREMIUM') return 'PREMIUM';
    if (normalized === 'FREE') return 'FREE';
    return normalized;
  }

  function normalizeTierTarget(target) {
    if (!target) return '';
    const normalized = userTier(target.textContent);
    if (normalized === 'PREMIUM' && target.textContent !== 'Premium') target.textContent = 'Premium';
    if (normalized === 'FREE' && target.textContent !== 'Free') target.textContent = 'Free';
    return normalized;
  }

  function normalizeLegacyTierCopy() {
    document.querySelectorAll('[data-email-pref-tier]').forEach(target => normalizeTierTarget(target));
    document.querySelectorAll('[data-email-health-tier]').forEach(target => {
      const text = String(target.textContent || '');
      const normalized = text
        .replace(/\bTRIAL\b/gi, 'Premium')
        .replace(/\bPAID\b/gi, 'Premium')
        .replace(/\bFREE\b/gi, 'Free');
      if (normalized !== text) target.textContent = normalized;
    });
    document.querySelectorAll('[data-product-email-tier-note],[data-email-health-note],.auth-security-note').forEach(target => {
      const text = String(target.textContent || '');
      const normalized = text
        .replace(/Trial\s*\/\s*Paid/gi, 'Premium')
        .replace(/Trial\s*\/\s*Premium/gi, 'Premium')
        .replace(/Trial\s+hoặc\s+Paid/gi, 'Premium')
        .replace(/Trial\s+hoặc\s+Premium/gi, 'Premium');
      if (normalized !== text) target.textContent = normalized;
    });
  }

  function render(card, tier) {
    if (tier !== 'FREE') {
      card.hidden = true;
      card.innerHTML = '';
      return;
    }

    card.hidden = false;
    card.className = 'account-upgrade-card';
    card.innerHTML = `
      <div class="account-upgrade-inner">
        <div>
          <span class="account-upgrade-kicker">FREE → PREMIUM</span>
          <h2>Mở báo cáo và cảnh báo dành cho Premium</h2>
          <p>Premium mở AI không giới hạn, báo cáo 09:00, kế hoạch giao dịch và cảnh báo hành động trong phiên.</p>
          <div class="account-upgrade-benefits">
            <span>AI không giới hạn</span>
            <span>Buy Zone · Stop · Target · R/R</span>
            <span>Action Alert · 10:30 · 11:15 · 13:30 · 14:15</span>
          </div>
        </div>
        <div class="account-upgrade-actions">
          <span class="account-upgrade-price">199.000đ <small>/ 30 ngày</small></span>
          <a href="${premiumUrl()}">Nâng Premium</a>
        </div>
      </div>`;
  }

  function mount() {
    const root = document.querySelector('[data-auth-account-details]');
    const tierTarget = document.querySelector('[data-account-tier]');
    if (!root || !tierTarget) return;
    const card = ensureCard(root);

    const refresh = () => {
      const tier = normalizeTierTarget(tierTarget);
      if (!tier || tier === '—') return;
      render(card, tier);
      normalizeLegacyTierCopy();
    };

    refresh();
    new MutationObserver(refresh).observe(tierTarget, { childList: true, subtree: true, characterData: true });
    new MutationObserver(normalizeLegacyTierCopy).observe(root, { childList: true, subtree: true, characterData: true });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
