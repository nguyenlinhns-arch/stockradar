# Changelog

## 2026-09-01 — V2 recommendation lifecycle and performance

- Separated research ranking from recommendation publication with a dedicated gate and fail-closed mode controls.
- Added immutable publication fields, deterministic first-zone-touch activation, performance entry, open/final/benchmark/excess returns and corporate-action handling.
- Added append-only recommendation/events/corporate-action/benchmark/manual-override tables and regression coverage for mutation attempts.
- Rebuilt public value around ticker search, recommendation lifecycle filters, a standalone Performance page and a nine-question stock report.
- Expanded Knowledge with publication-versus-activation, price/total return, benchmark, track-mode and anti-bias explanations.
- Added the twelve required V2 product, schema, lifecycle, methodology, rights, email, subscription, analytics, Ads and compliance documents.
- Replaced the first Ads round with Horizon Top, Ticker Search and Recommendation History; retained V1 Breakout/Risk creative only as historical assets.
- Migrated GPT instructions/API contract/regressions and analytics events to V2.
- Expanded regression to 57 tests and live route review to 23 pages.

## 2026-09-01 — GPT/stock-project integration

- Turned the GPT prototype into a constrained explanation layer over the same Data Grade, horizon, decision-gate and immutable-record contracts used by the engine.
- Added four distinct horizon score profiles and an immutable recommendation model/schema with five visibly MOCK records across all four horizons.
- Added sector × horizon, stock search, DEMO1 stock report, active recommendations, email schedule, watchlist and account/subscription contract pages.
- Added the original “Quy trình StockRadar” Knowledge guide covering data gates, score ≠ probability, anti-double-counting, twelve action gates, state lifecycle and email controls.
- Added email, authentication/watchlist and 30-day billing architecture contracts while keeping every production write blocked on GitHub Pages.
- Expanded automated coverage to 47 tests and 22 public routes plus health/API contract checks.

## 2026-09-01 — Professional finance-portal interface

- Rebuilt the visual system from a dark marketing layout into a compact Vietnamese finance-research portal with a neutral canvas, navy information hierarchy and restrained status colors.
- Added a shared utility bar, consistent task navigation and a data-status tape to every route.
- Redesigned Home around a Radar workspace, market-state sidebar, four goal tabs, research feed and an honest locked sector-ranking module.
- Redesigned Radar with a dense seven-column research table, Vietnamese state labels, legend, snapshot metadata and an explicit four-part Top 10 publication gate.
- Kept all fixture values visibly MOCK and avoided fake indices, fake news or inferred real-market rankings.
- Added regression checks for the portal shell, Radar workspace and truthful unavailable states.

## 2026-09-01 — Four-horizon positioning and Knowledge hub

- Reframed the homepage around Short, Medium, Long and Accumulation goals.
- Added accessible task-based navigation and a mobile menu across every public page.
- Added a Knowledge hub and six original, source-attributed guides covering CANSLIM/SEPA/VCP, VPA, 4M, Pocket Pivot, technical context and risk management.
- Documented UX patterns learned from FireAnt, FiinTrade, Simplize, SSI iBoard, VietstockFinance and CafeF while preserving StockRadar's narrow non-terminal scope.
- Aligned public copy with conditional Top 10/sector plans and 199,000/299,000 VND per 30-day pricing.
- Expanded regression coverage from 38 to 41 tests and local route checks from 7 to 14 public routes.

## 2026-09-01 — GitHub Pages launch

- Created and populated public repository `nguyenlinhns-arch/stockradar`.
- Added a GitHub Actions build that rebuilds MOCK data and requires all 38 tests to pass.
- Enabled Pages, deployed the static artifact and verified the public URL returned HTTP 200.
- Kept signup/event writes disabled and added `noindex,nofollow` while production data, privacy, compliance and brand gates remain open.

## 2026-09-01 — V1 local MVP

- Audited GPT package, method reference, OS V3.0 changelog and migration commands.
- Created StockRadar project structure and product specification.
- Implemented data gate, score, state machine, ranking and immutable ledger.
- Added MOCK fixture and public demo payload.
- Built Home, Radar 5, Breakout, Risk, Track Record, PRO and Signup pages.
- Added local lead/event API with minimal-data validation.
- Created six creative concepts in 4:5 and 9:16.
- Added campaign, analytics, UTM, Fanpage and GPT migration assets.
- Added regression and visual-QA workflow.
