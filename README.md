# StockRadar V1

StockRadar V1 is a deliberately small validation product:

`HOSE universe → data gate → score → setup state → Radar 5 → state-change alert → immutable track record`

The repository contains a working rules engine, append-only SQLite ledger, a mobile-first website, three acquisition propositions, analytics events, six ad concepts in two aspect ratios, and regression tests.

Important status: the included market records are labelled `MOCK`. They demonstrate the product and exercise the gates; they are not a live HOSE scan and can never be presented as “Top 5 HOSE”. A real release requires a licensed/current data feed, full-universe reconciliation, deployment, consent/privacy setup and compliance review.

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

- `STOCKRADAR_PRODUCT_SPEC.md` — product contract and V1 scope.
- `STOCKRADAR_BUILD_STATUS.md` — evidence-backed status by workstream.
- `STOCKRADAR_EXPERIMENTS.md` — append-only experiment registry.
- `engine/` — data gates, scoring, state machine, ranking and ledger.
- `website/` — Home, Radar 5, Breakout, Risk, Track Record and PRO pages; paths support both project Pages and a custom domain.
- `growth/` — ads, creatives, UTM and analytics.
- `gpt/` — migration contract for the old GPT prototype.

## Guardrails

- Score is evidence quality, not win probability.
- “Top 5 HOSE” is allowed only when the full-universe gate passes.
- Demo/mock data is visibly labelled in engine output and UI.
- Published snapshots are immutable; corrections are appended.
- StockRadar does not place orders and does not promise returns.
