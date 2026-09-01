# QA Report — StockRadar V1

## Automated result

Command:

```bash
python3 -m unittest discover -s engine/tests -v
```

Result: **42/42 PASS** on 2026-09-01.

Coverage includes:

- full-universe and MOCK claim gates;
- stale/missing/exclusion reconciliation;
- scoring Coverage and anti-double-count;
- score ≠ probability and OOS calibration conditions;
- intraday-volume method;
- state transition validity;
- extension/Market/R:R/stop/horizon buy gates;
- immutable snapshots and corrections;
- fourteen website routes, health, signup and event API;
- HTML metadata/internal assets;
- accessible mobile navigation on every page;
- Knowledge hub, six method guides, required source attribution and method sections;
- four-horizon positioning, conditional Top 10 language and 30-day pricing consistency;
- absence of the old personal brand in public web assets;
- professional portal shell, shared data-status tape and truthful Radar unavailable states;
- 6 Feed and 6 Reels image dimensions.

## GitHub Pages deployment QA

- Repository: `nguyenlinhns-arch/stockradar`.
- Workflow: `Verify and deploy StockRadar Pages`.
- Commit `ab2e273ad0981e78bf23ff9c4d2b1fa1648d58d4`.
- Run `33509617622`: **SUCCESS**.
- Build, 42-test regression suite, static artifact upload and Pages deploy: **PASS**.
- Live URL: `https://nguyenlinhns-arch.github.io/stockradar/`.
- All 14 public routes returned HTTP 200, including the Knowledge hub and six method guides.
- Public homepage contained the new dashboard, research feed, four horizons, locked sector module and truthful Top 10/pricing language.
- Public Radar payload remained visibly MOCK, `is_top5_hose=false`, and `SHORTLIST_FROM_AVAILABLE_DATA`.

## Live browser review of portal redesign

- Home at 1348px: no horizontal overflow; shared utility/header/data tape present; seven task links; five MOCK Radar rows loaded; neutral portal background and dashboard modules rendered.
- Radar at 1348px: no horizontal overflow; 937px main workspace plus 305px sidebar; dense table fits its panel; five rows, Vietnamese state labels and four publication-gate cards present.
- Knowledge hub at 1348px: no horizontal overflow; six method cards; active `Kiến thức` navigation and shared snapshot tape rendered.
- No site-origin JavaScript error was recorded. A browser-extension metadata error was excluded because it did not originate from the deployed website.

## Manual creative review

The 6-up contact sheet was inspected. First render failed small-label contrast; generator colors were corrected and all 12 assets were rendered again. Final creative review: **PASS** for legibility at source resolution and consistent disclaimer.

## Website visual screenshot blocker

The runtime contains the Playwright package but no Chromium executable. The new responsive layout therefore still requires live-browser inspection after deployment; local screenshot QA is **BLOCKED**, not claimed as PASS.

Static and integration checks still passed. Run:

```bash
python3 website/server.py --port 8765
STOCKRADAR_QA_URL=http://127.0.0.1:8765 node scripts/visual_qa.cjs
```

in an environment with Chromium installed. The script checks fourteen routes at 1440×1000 and 390×844, captures 28 screenshots and fails on console errors or horizontal overflow.

## Production QA not yet possible

- live HOSE data semantic correctness;
- full-universe reconciliation against an official/current master;
- alert delivery/idempotency;
- hosted privacy/consent deletion flow;
- production analytics attribution;
- Meta Ads delivery/policy result;
- custom-domain ownership, DNS and HTTPS configuration for `stockradar.vn`.
