const path = require('path');
const fs = require('fs');

function loadPlaywright() {
  const primary = process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES;
  if (primary) {
    try { return require(path.join(primary, 'playwright')); } catch (_) {}
  }
  return require('playwright');
}

const { chromium } = loadPlaywright();

const benignThirdPartyConsoleErrors = new Set([
  'Cannot listen to the event from the provided iframe, contentWindow is not available',
]);

function isBenignThirdPartyConsoleError(message) {
  return benignThirdPartyConsoleErrors.has(String(message || '').trim());
}

async function visibleFontViolations(page, selectors, minimumPx) {
  return page.locator(selectors).evaluateAll((nodes, min) => nodes
    .filter(node => {
      const style = getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0 && (node.textContent || '').trim();
    })
    .map(node => ({
      text: (node.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 70),
      px: parseFloat(getComputedStyle(node).fontSize || '0'),
    }))
    .filter(item => Number.isFinite(item.px) && item.px < min), minimumPx);
}

(async () => {
  const base = process.env.STOCKRADAR_QA_URL || 'http://127.0.0.1:8765';
  const out = path.resolve(__dirname, '..', 'artifacts', 'screenshots');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  const checks = [];
  const pages = [
    { name: 'home', route: '/' },
    { name: 'radar', route: '/radar5/' },
    { name: 'lookup', route: '/kiem-tra-co-phieu/' },
    { name: 'recommendations', route: '/khuyen-nghi/' },
    { name: 'sectors', route: '/nganh/' },
    { name: 'performance', route: '/hieu-qua/' },
    { name: 'today-changes', route: '/thay-doi-hom-nay/' },
    { name: 'newsletter', route: '/nhan-ban-tin/' },
    { name: 'plans', route: '/dang-ky/' },
    { name: 'signup', route: '/signup/?plan=free' },
    { name: 'login', route: '/dang-nhap/' },
    { name: 'checkout', route: '/thanh-toan/?plan=premium' },
    { name: 'account', route: '/tai-khoan/' },
    { name: 'stock', route: '/co-phieu/?ticker=FPT' },
    { name: 'breakout', route: '/breakout/' },
    { name: 'risk', route: '/risk/' },
    { name: 'track-record', route: '/track-record/' },
  ];
  const viewports = [
    { name: 'desktop', width: 1440, height: 1000 },
    { name: 'tablet', width: 768, height: 1024 },
    { name: 'mobile', width: 390, height: 844 },
    { name: 'mobile-small', width: 360, height: 800 },
    { name: 'mobile-large', width: 430, height: 932 },
  ];
  const bannedVisibleTerms = [
    'phương pháp', 'setup',
    '4m', 'canslim', 'sepa', 'vcp', 'vpa', 'rvol',
    'pocket pivot', 'early breakout', 'confirmed breakout', 'breakout', 'retest', 'payback',
    'wyckoff', 'minervini', 'o’neil', "o'neil", 'phil town',
    'ichimoku', 'bollinger', 'trendline', 'stage', 'pivot',
    'bear/base/bull', 'bear · base · bull', 'bear / base / bull',
  ];

  for (const viewport of viewports) {
    const context = await browser.newContext({
      viewport: { width: viewport.width, height: viewport.height },
      deviceScaleFactor: 1,
      reducedMotion: 'reduce',
    });

    for (const target of pages) {
      const page = await context.newPage();
      const routeErrors = [];
      const prefix = `${target.route} [${viewport.name}]`;
      page.on('console', msg => {
        if (msg.type() !== 'error') return;
        const text = msg.text();
        if (isBenignThirdPartyConsoleError(text)) return;
        routeErrors.push(`console: ${text}`);
      });
      page.on('pageerror', err => routeErrors.push(`pageerror: ${err.message}`));

      try {
        const response = await page.goto(base + target.route, { waitUntil: 'domcontentloaded', timeout: 15000 });
        await page.waitForTimeout(500);
        if (!response || response.status() !== 200) routeErrors.push(`HTTP ${response && response.status()}`);

        const structural = await page.evaluate(() => {
          const main = document.querySelector('main');
          const h1 = document.querySelector('h1');
          const overflow = document.documentElement.scrollWidth > document.documentElement.clientWidth + 2;
          const title = document.title.trim();
          const visibleText = (document.body.innerText || '').replace(/\s+/g, ' ').trim();
          const support = document.querySelector('a.sr-zalo-support');
          const supportRect = support?.getBoundingClientRect();
          const supportLabel = support?.querySelector('.sr-zalo-label');
          const labelRect = supportLabel?.getBoundingClientRect();
          const supportVisible = Boolean(supportRect && labelRect && supportRect.width >= 44 &&
            labelRect.width > 0 && labelRect.left >= 0 && supportRect.right <= innerWidth &&
            supportRect.bottom <= innerHeight && supportRect.top >= 0 &&
            support.contains(document.elementFromPoint(supportRect.x + supportRect.width / 2, supportRect.y + supportRect.height / 2)));
          const primaryControls = [...document.querySelectorAll(
            'button, .button, .lead-submit, .checkout-primary, .checkout-mobile-bar a, .nav-toggle, input[type="submit"]'
          )].filter(node => {
            const style = getComputedStyle(node);
            const rect = node.getBoundingClientRect();
            return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
          }).map(node => {
            const rect = node.getBoundingClientRect();
            return {
              text: (node.textContent || node.getAttribute('aria-label') || node.tagName).trim().slice(0, 80),
              width: Math.round(rect.width),
              height: Math.round(rect.height),
            };
          });
          return {
            hasMain: Boolean(main),
            hasH1: Boolean(h1 && h1.textContent.trim()),
            hasDecisionGuard: Boolean(document.querySelector('script[data-decision-copy-guard-v1]')),
            title,
            overflow,
            visibleText,
            primaryControls,
            supportVisible,
            supportHref: support?.getAttribute('href'),
          };
        });

        if (!structural.hasMain) routeErrors.push('missing <main>');
        if (!structural.hasH1) routeErrors.push('missing non-empty <h1>');
        if (!structural.hasDecisionGuard) routeErrors.push('decision-copy runtime guard missing');
        if (!structural.title) routeErrors.push('empty document title');
        if (structural.overflow) routeErrors.push('horizontal overflow');
        if (!structural.supportVisible) routeErrors.push('Zalo support button or label is hidden, covered or outside the viewport');
        if (structural.supportHref !== 'https://zalo.me/0398696879') routeErrors.push('incorrect Zalo support destination');

        const visibleTextLower = structural.visibleText.toLocaleLowerCase('vi');
        for (const term of bannedVisibleTerms) {
          if (visibleTextLower.includes(term.toLocaleLowerCase('vi'))) routeErrors.push(`visible analysis jargon: ${term}`);
        }

        if (viewport.name !== 'desktop') {
          for (const control of structural.primaryControls) {
            if (control.height < 36 && control.width < 36) routeErrors.push(`small primary control ${control.width}x${control.height}: ${control.text}`);
          }
        }

        if (target.name === 'home') {
          const sideVisible = await page.locator('.workspace-side').evaluateAll(nodes => nodes.some(node => {
            const style = getComputedStyle(node); const rect = node.getBoundingClientRect();
            return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
          }));
          if (sideVisible) routeErrors.push('homepage duplicate workspace sidebar is visible');
          const widths = await page.locator('.workspace-grid, .workspace-main').evaluateAll(nodes => nodes.map(node => Math.round(node.getBoundingClientRect().width)));
          if (widths.length >= 2 && widths[1] < widths[0] * 0.9) routeErrors.push(`AI workspace is not full width: ${widths.join('/')}`);
          if (viewport.name !== 'desktop') {
            const toggle = page.locator('[data-nav-toggle]').first();
            if (await toggle.count()) {
              await toggle.click();
              const expanded = await toggle.getAttribute('aria-expanded');
              if (expanded !== 'true') routeErrors.push('mobile nav toggle did not expand');
              await toggle.click();
            } else routeErrors.push('mobile nav toggle missing');
          }
        }

        if (target.name === 'recommendations') {
          const ledgerResponse = await page.request.get(base + '/public/data/recommendation-history.json');
          const ledger = await ledgerResponse.json();
          const expected = [...ledger.items].sort((a, b) => Date.parse(b.first_sent_at) - Date.parse(a.first_sent_at));
          const rows = page.locator('[data-verified-row]');
          const tickers = await rows.evaluateAll(nodes => nodes.map(node => node.dataset.ticker));
          if (JSON.stringify(tickers) !== JSON.stringify(expected.map(row => row.ticker))) routeErrors.push('verified recommendations missing or out of order');
          const cells = await rows.evaluateAll(nodes => nodes.map(node => node.querySelectorAll('td').length));
          if (cells.some(count => count !== 6)) routeErrors.push('verified prices overwritten by legacy runtime');
          if (await page.locator('.market-tape,.product-subnav').count()) routeErrors.push('legacy empty-data navigation returned');
          await page.waitForFunction(() => document.querySelector('[data-verified-controls]')?.disabled === false);
          if (expected.length) {
            await page.locator('[data-verified-search]').fill(expected[0].ticker.toLowerCase());
            if (await page.locator('[data-verified-row]:visible').count() !== 1) routeErrors.push('ticker filter did not isolate recommendation');
            await page.locator('[data-verified-row]:visible [data-rec-detail]').click();
            const detail = page.locator('#history-' + expected[0].ticker);
            if (!(await detail.evaluate(node => node.open))) routeErrors.push('recommendation details did not open');
            await detail.locator('summary').click();
          }
          await page.locator('[data-verified-search]').fill('000');
          if (await page.locator('[data-verified-row]:visible').count() !== 0 || !(await page.locator('[data-verified-empty]').isVisible())) routeErrors.push('empty filter state failed');
          await page.locator('[data-verified-reset]').click();
          if (await page.locator('[data-verified-row]:visible').count() !== expected.length) routeErrors.push('reset filter lost recommendations');
          await page.evaluate(() => { history.replaceState(null, '', location.pathname); window.scrollTo(0, 0); });
        }

        if (target.name === 'plans') {
          if (!(await page.locator('[data-plan-free]').count())) routeErrors.push('Free plan card missing');
          if (!(await page.locator('[data-plan-premium]').count())) routeErrors.push('Premium plan card missing');
          const tiny = await visibleFontViolations(page, '.plan-card p, .plan-card li, .plan-card .button, .plan-price-note', 10);
          if (tiny.length) routeErrors.push(`tiny plan text: ${tiny[0].px}px ${tiny[0].text}`);
        }

        if (target.name === 'signup') {
          if (!(await page.locator('[data-auth-signup-form]').count())) routeErrors.push('signup form missing');
          if ((await page.locator('input[name="selected_plan"]').count()) < 2) routeErrors.push('signup plan selector incomplete');
          if (!(await page.locator('[data-signup-submit-label]').count())) routeErrors.push('signup submit missing');
          const tiny = await visibleFontViolations(page, '.auth-card p, .auth-card label, .auth-card legend, .auth-card .auth-check, .auth-card .auth-security-note, .auth-card .button', 10);
          if (tiny.length) routeErrors.push(`tiny signup text: ${tiny[0].px}px ${tiny[0].text}`);
        }

        if (target.name === 'login') {
          if (!(await page.locator('[data-auth-login-form]').count())) routeErrors.push('login form missing');
          const tiny = await visibleFontViolations(page, '.auth-card p, .auth-card label, .auth-card .auth-security-note, .auth-card .auth-recovery, .auth-card .button', 10);
          if (tiny.length) routeErrors.push(`tiny login text: ${tiny[0].px}px ${tiny[0].text}`);
        }

        if (target.name === 'checkout') {
          if (!(await page.locator('[data-checkout-qr-image]').count())) routeErrors.push('checkout QR missing');
          if (!(await page.locator('[data-checkout-confirm]').count())) routeErrors.push('checkout confirmation missing');
          const account = String(await page.locator('[data-checkout-account-number]').first().textContent().catch(() => '') || '').trim();
          if (await page.locator('[data-checkout-payment]').isVisible()) routeErrors.push('checkout payment exposed without an authenticated, eligible request');
          if(await page.locator('[data-checkout-qr-image]').getAttribute('src'))routeErrors.push('checkout QR must remain absent before eligibility');
          if(!(await page.locator('[data-checkout-confirm]').isDisabled()))routeErrors.push('checkout confirmation enabled without a request');
          const tiny = await visibleFontViolations(page, '.checkout-card p, .checkout-bank-row, .checkout-warning, .checkout-confirm p, .checkout-state, .checkout-summary p, .checkout-features li, .checkout-note', 10);
          if (tiny.length) routeErrors.push(`tiny checkout text: ${tiny[0].px}px ${tiny[0].text}`);
        }

        if (target.name === 'stock') {
          if (!(await page.locator('[data-dynamic-stock-report]').count())) routeErrors.push('Free stock report target missing');
          if (!(await page.locator('[data-premium-stock-report]').count())) routeErrors.push('Premium stock report target missing');
          if (!(await page.locator('[data-premium-gate-copy]').count())) routeErrors.push('Premium gate copy missing');
          const tiny = await visibleFontViolations(page, '.commercial-stock-page .buyer-decision-strip span, .commercial-stock-page .analysis-tier-head p, .commercial-premium-row span, .commercial-premium-row strong', 10);
          if (tiny.length) routeErrors.push(`tiny stock text: ${tiny[0].px}px ${tiny[0].text}`);
        }

        checks.push({ route: target.route, viewport: viewport.name, status: routeErrors.length ? 'FAIL' : 'PASS' });
      } catch (error) {
        routeErrors.push(`navigation/check failed: ${error.message}`);
        checks.push({ route: target.route, viewport: viewport.name, status: 'FAIL' });
      }

      if (routeErrors.length) {
        routeErrors.forEach(error => errors.push(`${prefix}: ${error}`));
        try { await page.screenshot({ path: path.join(out, `${target.name}-${viewport.name}-ERROR.png`), fullPage: true }); } catch (_) {}
      }
      await page.close();
    }
    await context.close();
  }

  await browser.close();
  const report = {
    pages: pages.length,
    viewports: viewports.map(item => item.name),
    checks: checks.length,
    passed: checks.filter(item => item.status === 'PASS').length,
    failed: checks.filter(item => item.status === 'FAIL').length,
    errors,
  };
  fs.writeFileSync(path.join(out, 'visual-qa.json'), JSON.stringify(report, null, 2));
  process.stdout.write(`${JSON.stringify(report)}\n`);
  if (errors.length) process.exitCode = 1;
})().catch(error => {
  process.stderr.write(`${error.stack || String(error)}\n`);
  process.exitCode = 1;
});
