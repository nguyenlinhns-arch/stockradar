# Changelog

## 2026-09-02 — Public payload hardening

- Separated internal regression fixtures from the website data build.
- Replaced public Radar, recommendation, performance, journal, track-record and Today Changes rows with explicit fail-closed payloads.
- Removed all DEMO/MOCK records and labels from the published JSON and client runtime.
- Kept the 405/405 internal HOSE directory summary while publishing only 16 three-letter lookup references and no raw directory rows.
- Reduced the seven public JSON payloads from 71,518 bytes to 5,079 bytes by removing duplicated empty per-ticker reports.
- Changed the deployment workflow to rebuild only publication-safe data before tests and release.
- Removed unused legacy demo styling and made every public data loader gate on explicit operational status.

## 2026-09-02 — Operational interface and fail-closed HOSE data gate

- Removed rendered DEMO rankings, recommendation rows, performance statistics and Today Changes records from the main public product routes.
- Added compact operational status surfaces backed by the internal 405/405 HOSE directory reference while keeping raw directory rows out of the public artifact.
- Changed ticker search to accept any structurally valid three-letter code without falsely claiming public membership; unknown codes enter a controlled pending-verification state.
- Added device-local recent ticker history and tightened inputs to three letters with an autocomplete fallback.
- Blocked Radar, recommendation, performance, journal, track-record and change views whenever their payload fails the operational data gate.
- Preserved the Full-Universe, Data Rights and Recommendation gates; no price, score, rank or action is generated from missing data.
- Unified static asset cache keys across public routes.

## 2026-09-01 — Operational public interface

- Replaced the text-heavy Home with a working dashboard that opens directly to ticker lookup, market state, Radar, Today Changes and performance.
- Removed public methodology, Knowledge, backend-architecture and product-process explanations from the GitHub Pages artifact.
- Removed unavailable account, signup, watchlist, email and pricing routes from public deployment until their backends are connected.
- Reduced Radar, Trigger, Risk, Recommendation, Performance, Sector and History pages to their operative tables, filters and status views.
- Added state filters for Radar and a risk-alert view sourced from the same Today Changes payload.
- Kept internal method documents and implementation contracts in the repository; they are no longer part of the customer-facing website.
- Preserved the MOCK/SHADOW and noindex boundaries because a licensed live HOSE data source is not yet connected.

## 2026-09-01 — V2.1.2 universal lookup and service-monitoring update

- Applied Change Request V2.1, Execution Priority Addendum V2.1.1 and Change Request V2.1.2 without rebuilding the V2 core.
- Added independent new-position/holding assessments, mandatory review schedule/decisions and a fully attributed append-only recommendation journal.
- Added Today Changes, public no-recommendation state and explicit winners/losers/open/unactivated/closed history.
- Rebuilt Home around the ticker lookup live-demo flow; added `/kiem-tra-co-phieu/`, generic `/co-phieu/?ticker=...` and `/thay-doi-hom-nay/`.
- Replaced hard-coded client lookup with master-driven autocomplete, quick/partial results, per-horizon freshness and ticker-specific Trial CTA.
- Added SQLite report cache with independent horizon TTL, hit/miss/stale refresh, deduplicated watchlist monitoring and active intraday-universe union.
- Enforced Free transactional-only email, verified Trial/Paid product email, three-group onboarding and tier watchlist limits in domain policy/schema/UI.
- Expanded schemas for review, benchmark start/end, search/popularity, cache, monitored tickers, notification jobs and intraday universe.
- Added V2.1.2 analytics events, local API lookup/rate-limit reference and regression cases; kept Pages MOCK/SHADOW/noindex/no-write.
- Marked full current HOSE lookup, production on-demand analysis, auth/email/billing and Ads as BLOCKED until licensed data/backend/compliance exist.

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
