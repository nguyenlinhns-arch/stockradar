const path = require('path');
const fs = require('fs');
const { chromium } = require(path.join(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES, 'playwright'));

(async () => {
  const base = process.env.STOCKRADAR_QA_URL || 'http://127.0.0.1:8765';
  const out = path.resolve(__dirname, '..', 'artifacts', 'screenshots');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  const pages = [
    '/', '/radar5', '/breakout', '/risk', '/track-record', '/pro', '/signup',
    '/kien-thuc', '/kien-thuc/canslim-sepa', '/kien-thuc/vpa', '/kien-thuc/4m',
    '/kien-thuc/pocket-pivot', '/kien-thuc/cong-cu-ky-thuat',
    '/kien-thuc/quan-tri-rui-ro'
  ];
  for (const viewport of [{ name: 'desktop', width: 1440, height: 1000 }, { name: 'mobile', width: 390, height: 844 }]) {
    const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height }, deviceScaleFactor: 1 });
    for (const route of pages) {
      const page = await context.newPage();
      page.on('console', msg => { if (msg.type() === 'error') errors.push(`${route}: ${msg.text()}`); });
      page.on('pageerror', err => errors.push(`${route}: ${err.message}`));
      const response = await page.goto(base + route, { waitUntil: 'networkidle' });
      if (!response || response.status() !== 200) errors.push(`${route}: HTTP ${response && response.status()}`);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2);
      if (overflow) errors.push(`${route}: horizontal overflow`);
      const basename = route === '/' ? 'home' : route.slice(1).replaceAll('/', '-');
      await page.screenshot({ path: path.join(out, `${basename}-${viewport.name}.png`), fullPage: true });
      await page.close();
    }
    await context.close();
  }
  await browser.close();
  const report = { pages: pages.length, viewports: 2, screenshots: pages.length * 2, errors };
  fs.writeFileSync(path.join(out, 'visual-qa.json'), JSON.stringify(report, null, 2));
  process.stdout.write(JSON.stringify(report));
  if (errors.length) process.exitCode = 1;
})().catch(error => {
  process.stderr.write(error.stack || String(error));
  process.exitCode = 1;
});
