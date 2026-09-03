# STOCKRADAR BUILD STATUS V2.1.2 + OPERATIONAL DATA GATE

Updated: 2026-09-03 UTC. Allowed states: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `TESTING`, `PASS`, `FAILED`. A reference implementation may PASS while its production dependency remains a separate BLOCKED row.

| Workstream | Status | Evidence | Remaining production gate |
| --- | --- | --- | --- |
| V2.1.2 product contract | PASS | Current Product Spec plus personalization, Today Changes, journal and lookup/cache specs | Validate with real-user flow data |
| Four horizon scoring | PASS | Distinct models; anti-double-count/probability regressions | Licensed data and horizon-matched OOS calibration |
| Ranking ≠ Recommendation | PASS | Separate gate, extended Top-1 regression and empty-publication state | Calibrate on approved HOSE dataset |
| New-position / holding view | PASS | Independent domain assessment and dynamic ticker UI | Production evidence and compliant wording review |
| Publication/activation/P&L | PASS | First eligible post-publication touch; unactivated no P/L; closed final frozen | Production calendar/bar contract |
| Review due / journal | PASS | Models, JSON/SQL schemas, schedule, append-only triggers, public timeline and tests | Production DB/access control/backups |
| VN-Index benchmark method | PASS | Matching activation-to-current/close start/end demo and regression | Licensed benchmark provider/redistribution rights |
| Today Changes | PASS | Significant-event filter, payload, 30–60 second route | Production event pipeline |
| Public recommendation history | PASS | Winner, loser, open, unactivated and closed SHADOW records; no cherry-pick | Forward production sample |
| Ticker lookup UI | PASS | Three-letter validation, fixture autocomplete, structurally valid unknown-ticker acceptance, dynamic route and device-local recent history | Public membership verification remains gated |
| Dynamic ticker route | PASS | Generic client route, local `/co-phieu/{ticker}` resolver and Pages 404 redirect | Server-side SSR/indexability after rights/compliance |
| Per-horizon cache/on-demand interface | PASS | SQLite hit/miss/stale/refresh, independent TTL and tests | Durable production cache, queue, invalidation and observability |
| Watchlist dedupe / active intraday set | PASS | One ticker pipeline, subscriber fan-out and union regression | Authenticated durable store and worker |
| Free email restriction | PASS | Tier policy, schema/UI/spec and regression | Production enforcement after auth/email connection |
| Trial/Paid personalization | PASS | Preferences, limits, content prioritization and UI | Managed auth, verification, consent and delivery provider — BLOCKED |
| Analytics V2.1.2 | PASS | Search/cache/report/onboarding/holding/journal event allowlists/spec | First-party store, identity/bot filtering and consent |
| Website operational shell | PASS | Main routes and published JSON contain no sample rankings, recommendations, performance or changes; every unavailable surface fails closed to a compact status | Real-device/mobile matrix before production |
| Internal HOSE directory reference | PASS | Drive snapshot `hose-universe-2026-09-02-065632-vn`; 405/405 records structurally validated | Listing-status semantics and public redistribution rights remain unresolved |
| Production data contract / publication gate | PASS | `engine/stockradar/production_data.py`, CLI validator, contract document and regression tests; Pages rejects any production-looking payload without a valid fresh rights-aware manifest | Licensed production bundle and written rights evidence |
| Automated regression | PASS | GitHub Actions regression suite passed on commit `70497fa`; includes production-data and Pages publication-gate tests | Production adapter/E2E tests with licensed provider |
| Static GitHub Pages | PASS | Fail-closed public-data build, static artifact and production auth verification passed in GitHub Actions; 12 read-only product routes + 404 | Production data/auth/compliance remain separately BLOCKED |
| Full current HOSE market data/rights | BLOCKED | Internal directory coverage is 405/405; Drive `Giá & OHLCV` and `Dữ liệu doanh nghiệp` contain no production payload. DNSE LightSpeed is technically suitable for internal scanning but its current terms prohibit third-party redistribution, including processed data, without written approval. FiinGroup API Datafeed is a technical candidate only. | Contracted source with public display + redistribution + derived-data rights; current master/OHLCV/fundamentals/event/corporate-action bundle; active-status semantics and reconciliation |
| Production anonymous rate limit | BLOCKED | Configurable local reference limiter passes tests | Server-side gateway/WAF/rate limiter; Pages cannot enforce |
| Auth/watchlist persistence | BLOCKED | Schemas, tier limits and honest UI only | Managed auth, secure DB, threat model and privacy operations |
| Email delivery | BLOCKED | Trial/Paid-only personalized contract and UI | Provider, verified domain, consent, unsubscribe, bounce/complaint, worker |
| Billing/subscription | BLOCKED | Exact 30-day contract and 199k/299k hypotheses | Provider/webhooks, reconciliation, tax/refund/security/compliance |
| Compliance/legal | BLOCKED | RESEARCH_ONLY/noindex, data-rights registry and formal checklist | Authorized Vietnamese legal/compliance approval |
| Ads first round | BLOCKED | Lookup, holding and history landings/events are implemented; spending not authorized | Production data/auth/measurement, six approved assets, compliance and account eligibility |

## Shipping conclusion

Operational static interface, fail-closed data build and production-data publication gate: **PASS in GitHub Actions**.

Any structurally valid three-letter ticker can enter the public lookup flow. Verified current-HOSE membership, live Top HOSE, production recommendations/performance, customer-facing DNSE-derived signals, email delivery, payment and Ads remain **BLOCKED**.

Critical path: `licensed public/derived-data rights → fresh production manifest + full-universe bundle → reconciliation → production API/cache/queue/rate limit → auth/privacy → email/billing → formal compliance → PRODUCTION_APPROVED`.
