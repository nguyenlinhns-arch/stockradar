# QA Report — StockRadar V2.1.2

Date: 2026-09-01 UTC.

## Release result

Research-only V2.1.2: **PASS**.

- Functional release commit: `3f61ad6f328d7dedf22bf5370778ede875360a01`.
- GitHub Actions run: `33532527570` — SUCCESS.
- Live URL: `https://nguyenlinhns-arch.github.io/stockradar/`.
- Public mode: `RESEARCH_ONLY · MOCK · SHADOW`, no writes, `noindex,nofollow`.

Production data, all-current-HOSE lookup, recommendations, auth, email, billing, Ads and compliance remain BLOCKED by their documented gates.

## Automated verification

`python -m unittest discover -s engine/tests -v`: **79/79 PASS**.

Coverage includes:

- four distinct horizon models and score/probability boundaries;
- ranking versus recommendation and the valid no-recommendation state;
- first post-publication activation, no P/L before activation and frozen closed results;
- independent new-position/holding assessments;
- mandatory review schedule and append-only correction/event journal;
- VN-Index matching-window benchmark fields;
- Free versus Trial/Paid email entitlements and personalized onboarding;
- ticker normalization, non-original ticker lookup, cache miss/hit/stale refresh and independent horizon TTL;
- deduplicated monitoring, subscriber fan-out and active intraday-universe union;
- Today Changes significance filtering, server rate limiting and partial-data API states;
- static metadata/assets, truthful data boundaries, responsive navigation and Pages build.

Additional checks:

- deterministic demo build: PASS;
- Python compilation: PASS;
- `node --check website/assets/app.js`: PASS;
- JSON parsing: 15/15 files PASS;
- CSS braces: 813/813 pairs PASS;
- Pages artifact: 26 routes plus `404.html`, API disabled and `noindex,nofollow` PASS.

## Live interaction review

At the inspected desktop viewport:

- Home rendered the V2.1.2 lookup-first hero, six-value summary, Radar snapshot and public performance preview.
- Typing `VC` exposed exactly the `VCI` master-driven option; selecting it returned a four-horizon quick result with licensed-data blocking instead of fabricated price/rank/score.
- The VCI report rendered partial-data explanations, separate new-position/holding states, no fake recommendation and no fake journal.
- DEMO1 rendered all four horizons, independent position views, public history, review due/status and two immutable journal events.
- Today Changes rendered three significant MOCK changes.
- Recommendations rendered five records; the `Chưa kích hoạt` filter reduced the view to exactly DEMO2. Review due/status columns and 11 journal events were present.
- `/co-phieu/VCI/` redirected to the generic ticker report and preserved the ticker.
- `signup/?tier=trial&ticker=VCI` selected Trial and prefilled VCI while preserving the verified-consent email boundary.
- Unknown `ZZZ` produced the explicit incomplete-master boundary; it did not fabricate a report.
- The live artifact exposed `data-api-mode="disabled"` and `noindex,nofollow`; no website-origin console warning/error was observed.

## Remaining QA gates

The cloud browser cannot access the local `127.0.0.1` preview and does not expose a mobile viewport switch. Responsive CSS and navigation regressions pass, but a real-device mobile screenshot matrix is still required before production approval.

Production QA cannot begin until licensed HOSE/master/benchmark/corporate-action data, secure backend/cache/queue/rate limiting, auth/privacy, email/billing and formal Vietnamese compliance approval exist.
