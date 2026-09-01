# StockRadar V2

**Live static demo:** https://nguyenlinhns-arch.github.io/stockradar/

StockRadar V2 is a deliberately focused validation product:

`HOSE universe → data gate → horizon ranking → recommendation gate → publication → activation → immutable performance`

The repository contains a validation rules engine, four horizon-specific score profiles, a separate recommendation gate, deterministic activation/performance logic, an append-only SQLite ledger, a mobile-first Vietnamese research portal, Knowledge hub, acquisition/analytics contracts and regression tests.

Important status: the included market records are labelled `MOCK`. They demonstrate the product and exercise the legacy five-item gate; they are not a live HOSE scan and can never be presented as a real “Top 10 HOSE”. A real release requires a licensed/current data feed, four validated horizon models, full-universe reconciliation, consent/privacy setup and compliance review.

## Run locally

```bash
python3 -m engine.cli build-demo
python3 -m unittest discover -s engine/tests -v
python3 website/server.py --port 8080
```

Then open `http://127.0.0.1:8080`.

## Deploy with GitHub Pages

The repository includes `.github/workflows/pages.yml`. On every push to `main`, it rebuilds the MOCK payload, runs all regression tests, produces a static-only artifact and deploys it with GitHub Pages.

```bash
python3 scripts/build_pages.py --output .pages-site
python3 -m http.server 8081 --directory .pages-site
```

The Pages artifact deliberately disables signup/event submission because GitHub Pages cannot run the Python API. See `docs/GITHUB_PAGES_DEPLOYMENT.md` for repository, domain and backend gates.

## Core deliverables

- `STOCKRADAR_PRODUCT_SPEC_V2.md` — current product contract and V2 scope.
- `STOCKRADAR_BUILD_STATUS.md` — evidence-backed status by workstream.
- `STOCKRADAR_EXPERIMENTS.md` — append-only experiment registry.
- `engine/` — data gates, scoring, state machine, ranking and ledger.
- `website/` — Home, horizon Radar, sector matrix, recommendation lifecycle, nine-question stock report, Performance, email, watchlist/account contracts, Knowledge, pricing and signup pages.
- `docs/UX_BENCHMARK_VI.md` — patterns learned from established Vietnamese finance products and the boundaries retained for StockRadar.
- `growth/` — ads, creatives, UTM and analytics.
- `gpt/` — migration contract for the old GPT prototype.

## Guardrails

- Score is evidence quality, not win probability.
- “Top 10 HOSE” is allowed only when the full-universe and selected-horizon gates pass.
- Demo/mock data is visibly labelled in engine output and UI.
- Published snapshots are immutable; corrections are appended.
- Publication is not activation; unactivated records have no P/L.
- Closed results are frozen and BACKTEST/SHADOW/LIVE_PUBLISHED remain separate.
- StockRadar does not place orders and does not promise returns.
