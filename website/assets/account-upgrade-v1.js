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

  function render(card, tier) {
    const normalized = String(tier || '').trim().toUpperCase();
    if (!['FREE', 'TRIAL'].includes(normalized)) {
      card.hidden = true;
      card.innerHTML = '';
      return;
    }

    const trial = normalized === 'TRIAL';
    card.hidden = false;
    card.className = `account-upgrade-card${trial ? ' is-trial' : ''}`;
    card.innerHTML = `
      <div class="account-upgrade-inner">
        <div>
          <span class="account-upgrade-kicker">${trial ? 'TRIAL → PREMIUM' : 'FREE → PREMIUM'}</span>
          <h2>${trial ? 'Giữ quyền cảnh báo sau khi Trial kết thúc' : 'Nâng Premium khi bạn cần hành động trong phiên'}</h2>
          <p>${trial
            ? 'Premium tiếp tục các quyền phân tích sâu và cảnh báo mua/bán sau thời gian Trial.'
            : 'Free đã có bản rà soát 09:00. Premium bổ sung phần đáng trả phí nhất: kế hoạch giao dịch và cảnh báo hành động trong phiên.'}</p>
          <div class="account-upgrade-benefits">
            <span>Buy Zone · Stop · Target · R/R</span>
            <span>10:30 · 11:15 · 13:30 · 14:15</span>
            <span>Khoảng 20 mã theo dõi</span>
          </div>
        </div>
        <div class="account-upgrade-actions">
          <span class="account-upgrade-price">199.000đ <small>/ 30 ngày</small></span>
          <a href="${premiumUrl()}">${trial ? 'Gia hạn bằng Premium' : 'Nâng Premium'}</a>
        </div>
      </div>`;
  }

  function mount() {
    const root = document.querySelector('[data-auth-account-details]');
    const tierTarget = document.querySelector('[data-account-tier]');
    if (!root || !tierTarget) return;
    const card = ensureCard(root);

    const refresh = () => {
      const tier = String(tierTarget.textContent || '').trim();
      if (!tier || tier === '—') return;
      render(card, tier);
    };

    refresh();
    new MutationObserver(refresh).observe(tierTarget, { childList: true, subtree: true, characterData: true });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
