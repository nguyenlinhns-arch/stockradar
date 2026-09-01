# StockRadar V2.1.2

**Live static demo:** https://nguyenlinhns-arch.github.io/stockradar/

StockRadar V2.1.2 is a deliberately focused validation product:

`light full-HOSE scan → ticker lookup / ranking → on-demand deep analysis + cache → recommendation gate → activation / review / performance → deduplicated monitoring`

The repository contains a validation engine, four horizon-specific score profiles, separate recommendation gate, dynamic ticker lookup contract, per-horizon report cache, deterministic activation/review/performance logic, append-only SQLite journal, personalization/email entitlements, ticker-level monitor deduplication, a mobile-first Vietnamese research portal, Knowledge hub, analytics contracts and regression tests.

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
- `engine/` — data gates, scoring, ranking/recommendation, lookup/cache, personalization, monitoring and immutable ledger.
- `website/` — lookup-first Home, `/kiem-tra-co-phieu/`, dynamic ticker reports, Today Changes, recommendation journal/history, Performance, paid email, watchlist/account contracts, Knowledge, pricing and onboarding.
- `docs/UX_BENCHMARK_VI.md` — patterns learned from established Vietnamese finance products and the boundaries retained for StockRadar.
- `growth/` — ads, creatives, UTM and analytics.
- `gpt/` — migration contract for the old GPT prototype.

## Guardrails

- Score is evidence quality, not win probability.
- “Top 10 HOSE” is allowed only when the full-universe and selected-horizon gates pass.
- Demo/mock data is visibly labelled in engine output and UI.
- Published snapshots are immutable; corrections are appended.
- Publication is not activation; unactivated records have no P/L.
- New-position and holding views are independent; `KHÔNG MUA ĐUỔI` is not an automatic sell.
- Free users receive transactional email only; verified Trial/Paid consent is required for product email.
- On-demand lookup never replaces the full-universe gate for Top-HOSE claims.
- Closed results are frozen and BACKTEST/SHADOW/LIVE_PUBLISHED remain separate.
- StockRadar does not place orders and does not promise returns.
