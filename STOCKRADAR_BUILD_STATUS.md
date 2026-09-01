# STOCKRADAR BUILD STATUS V2.1.2

Updated: 2026-09-01 UTC. Allowed states: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `TESTING`, `PASS`, `FAILED`. A reference implementation may PASS while its production dependency remains a separate BLOCKED row.

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
| Ticker lookup UI | PASS | Master-driven autocomplete, uppercase validation, quick/partial result and Trial CTA | None for MOCK fixture |
| Dynamic ticker route | PASS | Generic client route, local `/co-phieu/{ticker}` resolver and Pages 404 redirect | Server-side SSR/indexability after rights/compliance |
| Per-horizon cache/on-demand interface | PASS | SQLite hit/miss/stale/refresh, independent TTL and tests | Durable production cache, queue, invalidation and observability |
| Watchlist dedupe / active intraday set | PASS | One ticker pipeline, subscriber fan-out and union regression | Authenticated durable store and worker |
| Free email restriction | PASS | Tier policy, schema/UI/spec and regression | Production enforcement after auth/email connection |
| Trial/Paid personalization | PASS | Preferences, limits, content prioritization and UI | Managed auth, verification, consent and delivery provider — BLOCKED |
| Analytics V2.1.2 | PASS | Search/cache/report/onboarding/holding/journal event allowlists/spec | First-party store, identity/bot filtering and consent |
| Website V2.1.2 | PASS | Operational Home; ticker lookup; Radar filters; Trigger/Risk; Today Changes; recommendation, performance, sector and history views; public explanatory/blocked routes removed | Real-device/mobile matrix before production |
| Automated regression | PASS | 79/79 tests; static build; JS syntax; public-route/link checks | Production adapter/E2E tests |
| Static GitHub Pages | PASS | 12 read-only product routes + 404; no-write, noindex, MOCK/SHADOW; Knowledge and unavailable service routes excluded | Production data/auth/compliance remain separately BLOCKED |
| Full current HOSE master/data/rights | BLOCKED | Fixture is explicitly `full_universe=false`, `MOCK` | Licensed current master/price/fundamental/event/corporate-action data and reconciliation |
| Production anonymous rate limit | BLOCKED | Configurable local reference limiter passes tests | Server-side gateway/WAF/rate limiter; Pages cannot enforce |
| Auth/watchlist persistence | BLOCKED | Schemas, tier limits and honest UI only | Managed auth, secure DB, threat model and privacy operations |
| Email delivery | BLOCKED | Trial/Paid-only personalized contract and UI | Provider, verified domain, consent, unsubscribe, bounce/complaint, worker |
| Billing/subscription | BLOCKED | Exact 30-day contract and 199k/299k hypotheses | Provider/webhooks, reconciliation, tax/refund/security/compliance |
| Compliance/legal | BLOCKED | RESEARCH_ONLY/noindex and formal checklist | Authorized Vietnamese legal/compliance approval |
| Ads first round | BLOCKED | Lookup, holding and history landings/events are implemented; spending not authorized | Production data/auth/measurement, six approved assets, compliance and account eligibility |

## Shipping conclusion

Research-only V2.1.2 operational interface: **PASS**.

Production StockRadar, “any current HOSE ticker,” live Top HOSE, production recommendations/performance, email delivery, payment and Ads: **BLOCKED**.

Critical path: `licensed data/rights → full-universe reconciliation → production API/cache/queue/rate limit → auth/privacy → email/billing → formal compliance → PRODUCTION_APPROVED`.
