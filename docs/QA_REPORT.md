# QA Report — StockRadar V2

Date: 2026-09-01 UTC.

## Automated result

`python -m unittest discover -s engine/tests -v`: **57/57 PASS**.

Coverage includes full-universe/MOCK gates, four distinct horizons, evidence anti-double-count, score/probability boundary, Recommendation Gate, first post-publication activation, no P/L before activation, corporate-action price/total return, unresolved-rights blocking, benchmark/excess fields, frozen closed results, append-only recommendation events, all required V2 contract documents, analytics/server boundaries, metadata/assets, responsive navigation, static Pages build and 23 application routes plus health/API tests.

Additional checks:

- `node --check website/assets/app.js`: PASS;
- CSS opening/closing braces: 669/669;
- JSON parsing for recommendation, analytics and GPT regression schemas: PASS;
- Pages build includes `/hieu-qua/`, disables write API and injects `noindex,nofollow`: PASS.

## Deployment

- Repository: `nguyenlinhns-arch/stockradar`.
- V2 core commit: `020f22c393c606353319de295ed26ed7af419e6c`.
- GitHub Actions run: `33526215030` — SUCCESS.
- Live URL: `https://nguyenlinhns-arch.github.io/stockradar/`.
- All 23 public routes produced a title and H1, no 404 state and no document-level horizontal overflow at the inspected desktop viewport.

## Live interaction review

- Home: V2/RESEARCH_ONLY chrome, seven-task navigation, ticker search, three public recommendation rows and performance summary rendered. DEMO1 search returned the nine-question report CTA.
- Khuyến nghị: five lifecycle records rendered. Clicking `Chưa kích hoạt · 1` reduced the table to exactly DEMO2; its activation/entry/P&L are blank/CHƯA KÍCH HOẠT. Wide research columns remain contained in the table's own horizontal scroller.
- Hiệu quả: six summary cards and five records rendered; one unactivated, two open, two closed. Win rate is 50.00% and states explicitly that only closed records form the denominator.
- DEMO1: nine answer cards, publication price, activation timestamp, performance entry and +0.79% open P/L rendered; no document overflow.
- No website-origin console error was observed. Browser-extension metadata errors were excluded because their URL was `chrome-extension://`, not the deployed site.

## Remaining QA gates

Local cloud-browser access to `127.0.0.1` was unavailable, so live deployment was used for rendered inspection. The responsive CSS/navigation tests pass, but a real-device/mobile screenshot matrix remains required before production launch.

Production QA is not possible until licensed HOSE data, a full-universe adapter, corporate-action/benchmark sources, secure auth/privacy, email/billing services and formal compliance approval exist.
