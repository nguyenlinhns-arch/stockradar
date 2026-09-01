# QA Report — StockRadar V1

## Automated result

Command:

```bash
python3 -m unittest discover -s engine/tests -v
```

Result: **41/41 PASS** on 2026-09-01.

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
- 6 Feed and 6 Reels image dimensions.

## GitHub Pages deployment QA

- Repository: `nguyenlinhns-arch/stockradar`.
- Workflow: `Verify and deploy StockRadar Pages`.
- Commit `81172644b7ac53d3da3cbc2c2a18aa9ae1147d20`.
- Run `33504751657`: **SUCCESS**.
- Build, 41-test regression suite, static artifact upload and Pages deploy: **PASS**.
- Live URL: `https://nguyenlinhns-arch.github.io/stockradar/`.
- All 14 public routes returned HTTP 200, including the Knowledge hub and six method guides.
- Public homepage contained the expected four-horizon/Top 10/pricing copy and had `data-api-mode="disabled"` plus `noindex,nofollow`.
- Public Radar payload remained visibly MOCK, `is_top5_hose=false`, and `SHORTLIST_FROM_AVAILABLE_DATA`.

## Live browser review

- Home at 1363×936: no horizontal overflow; expected title/H1; four horizon cards; six method links; five MOCK Radar rows; desktop task navigation visible.
- Knowledge hub: no horizontal overflow; six method cards; four horizon explanations; five method-to-engine table rows.
- CANSLIM/SEPA article: no horizontal overflow; five contents links; five article sections; StockRadar-application and source sections present.
- Navigation from Home → Knowledge → CANSLIM/SEPA succeeded through visible links.
- No site-origin JavaScript error was recorded. Browser-extension metadata errors were excluded because they did not originate from the deployed website.

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
