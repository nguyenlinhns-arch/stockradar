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
    { name: 'login', route: '/dang-nhap/' },
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
  ];
  const bannedVisibleTerms = [
    'phân tích', 'phương pháp', 'setup',
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
          };
        });

        if (!structural.hasMain) routeErrors.push('missing <main>');
        if (!structural.hasH1) routeErrors.push('missing non-empty <h1>');
        if (!structural.hasDecisionGuard) routeErrors.push('decision-copy runtime guard missing');
        if (!structural.title) routeErrors.push('empty document title');
        if (structural.overflow) routeErrors.push('horizontal overflow');

        const visibleTextLower = structural.visibleText.toLocaleLowerCase('vi');
        for (const term of bannedVisibleTerms) {
          if (visibleTextLower.includes(term.toLocaleLowerCase('vi'))) {
            routeErrors.push(`visible analysis jargon: ${term}`);
          }
        }

        if (viewport.name !== 'desktop') {
          for (const control of structural.primaryControls) {
            if (control.height < 36 && control.width < 36) {
              routeErrors.push(`small primary control ${control.width}x${control.height}: ${control.text}`);
            }
          }
        }

        if (target.name === 'home' && viewport.name !== 'desktop') {
          const toggle = page.locator('[data-nav-toggle]').first();
          if (await toggle.count()) {
            await toggle.click();
            const expanded = await toggle.getAttribute('aria-expanded');
            if (expanded !== 'true') routeErrors.push('mobile nav toggle did not expand');
            await toggle.click();
          } else {
            routeErrors.push('mobile nav toggle missing');
          }
        }

        checks.push({ route: target.route, viewport: viewport.name, status: routeErrors.length ? 'FAIL' : 'PASS' });
      } catch (error) {
        routeErrors.push(`navigation/check failed: ${error.message}`);
        checks.push({ route: target.route, viewport: viewport.name, status: 'FAIL' });
      }

      if (routeErrors.length) {
        routeErrors.forEach(error => errors.push(`${prefix}: ${error}`));
        try {
          await page.screenshot({ path: path.join(out, `${target.name}-${viewport.name}-ERROR.png`), fullPage: true });
        } catch (_) {}
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
