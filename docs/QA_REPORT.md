# QA Report — StockRadar V1

## Automated result

Command:

```bash
python3 -m unittest discover -s engine/tests -v
```

Result: **38/38 PASS** on 2026-09-01.

Coverage includes:

- full-universe and MOCK claim gates;
- stale/missing/exclusion reconciliation;
- scoring Coverage and anti-double-count;
- score ≠ probability and OOS calibration conditions;
- intraday-volume method;
- state transition validity;
- extension/Market/R:R/stop/horizon buy gates;
- immutable snapshots and corrections;
- seven website routes, health, signup and event API;
- HTML metadata/internal assets;
- absence of the old personal brand in public web assets;
- 6 Feed and 6 Reels image dimensions.

## GitHub Pages deployment QA

- Repository: `nguyenlinhns-arch/stockradar`.
- Workflow: `Verify and deploy StockRadar Pages`.
- Run `33500186454`, attempt 2: **SUCCESS**.
- Build, 38-test regression suite, static artifact upload and Pages deploy: **PASS**.
- Live URL: `https://nguyenlinhns-arch.github.io/stockradar/`.
- Public homepage returned HTTP 200, contained the expected StockRadar title and had `data-api-mode="disabled"`.
- Public Radar payload remained visibly MOCK, `is_top5_hose=false`, and `SHORTLIST_FROM_AVAILABLE_DATA`.

## Manual creative review

The 6-up contact sheet was inspected. First render failed small-label contrast; generator colors were corrected and all 12 assets were rendered again. Final creative review: **PASS** for legibility at source resolution and consistent disclaimer.

## Website visual screenshot blocker

The runtime contained the Playwright package but no Chromium executable. A browser install attempt timed out on the browser CDN. Therefore browser screenshots and pixel-level desktop/mobile inspection are **BLOCKED**, not claimed as PASS.

Static and integration checks still passed. Run:

```bash
python3 website/server.py --port 8765
STOCKRADAR_QA_URL=http://127.0.0.1:8765 node scripts/visual_qa.cjs
```

in an environment with Chromium installed. The script checks seven routes at 1440×1000 and 390×844, captures 14 screenshots and fails on console errors or horizontal overflow.

## Production QA not yet possible

- live HOSE data semantic correctness;
- full-universe reconciliation against an official/current master;
- alert delivery/idempotency;
- hosted privacy/consent deletion flow;
- production analytics attribution;
- Meta Ads delivery/policy result;
- custom-domain ownership, DNS and HTTPS configuration for `stockradar.vn`.
