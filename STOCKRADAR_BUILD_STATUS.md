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
| Per-horizon cache/on-demand interface | PASS | SQLite hit/miss/stale/refresh, independent TTL and tests | Production cache population from licensed bundle |
| Watchlist dedupe / active intraday set | PASS | One ticker pipeline, subscriber fan-out and union regression | Notification worker after data/email gates |
| Free email restriction | PASS | Tier policy plus database entitlement trigger; Free product email cannot be enabled | Provider/delivery gate remains closed |
| Trial/Paid personalization | PASS | Supabase `user_preferences` + `watchlist_items`, RLS, server-side 3/20 limits, account UI and deployed regression | Live signed-in browser E2E and production data |
| Analytics V2.1.2 | PASS | Search/cache/report/onboarding/holding/journal event allowlists/spec | First-party store, identity/bot filtering and consent |
| Website operational shell | PASS | Main routes and published JSON contain no sample rankings, recommendations, performance or changes; every unavailable surface fails closed to a compact status | Real-device/mobile matrix before production |
| Internal HOSE directory reference | PASS | Drive snapshot `hose-universe-2026-09-02-065632-vn`; 405/405 records structurally validated | Listing-status semantics and public redistribution rights remain unresolved |
| Production data contract / publication gate | PASS | Rights-aware manifest validation plus Pages deployment guard | Licensed production bundle and written rights evidence |
| Licensed bundle assembler | PASS | Provider-neutral CSV assembler requires `snapshot.exchange=HOSE`, validates HOSE on security master, rejects OHLCV/fundamental tickers outside master, computes SHA-256/coverage and same-snapshot manifest | Supplier must deliver approved HOSE master/OHLCV/fundamentals/corporate-actions/events bundle |
| Supabase auth foundation | TESTING | Production project `StockRadar` active in Singapore; profiles/consent RLS; account-delete Edge Function JWT-protected; public-table security posture reviewed | Signed-in browser E2E, recovery/delete flow matrix and privacy-operations drill |
| Auth/watchlist persistence | TESTING | Production Supabase migration `20260903043404`; anon has no access, authenticated own-row RLS; account UI deployed; server-side tier limit | Signed-in browser E2E with Free/Trial/Paid fixtures |
| Authenticated production API gateway / rate limit | TESTING | Supabase `stock-api` Edge Function ACTIVE with JWT verification; private report cache; service-role-only RPCs; server-side per-user/tier quotas; API safe-enable gate defaults false | Signed-in browser E2E, licensed cache writer and production gate evidence |
| Anonymous dynamic production API | PASS | Not offered by design. Anonymous visitors use static/public surfaces; licensed production cache is never exposed directly through Pages/Data API | Revisit only if product policy later requires anonymous live data |
| Product-email consent/outbox gate | PASS | Supabase product-email preferences, append-only consent events, private outbox/suppressions and fail-closed delivery gate | Provider-specific worker/webhooks remain separate |
| Billing foundation / gate | PASS | Private provider-neutral plans, anti-replay payment events, verified 30-day grants and fail-closed checkout gate; checkout remains disabled | Payment provider, signed webhooks, reconciliation, refund/chargeback, tax/compliance approval |
| Automated regression | PASS | GitHub Actions build/regression/static/auth verification passed after strict HOSE-only bundle tests; personalization, email, billing and API-gateway contracts are covered | Add signed-in/provider/data E2E when dependencies exist |
| Static GitHub Pages | PASS | Fail-closed public-data build, static artifact and production auth verification continue to pass | Production market data/compliance remain separately BLOCKED |
| Full current HOSE market data/rights | BLOCKED | Internal directory coverage is 405/405; Drive `Giá & OHLCV` and `Dữ liệu doanh nghiệp` contain no production payload. DNSE LightSpeed is suitable for internal scanning but current terms prohibit third-party redistribution, including processed data, without written approval. FiinGroup API Datafeed is a technical candidate only. | Contracted source with public display + redistribution + derived-data rights; current master/OHLCV/fundamentals/event/corporate-action bundle; active-status semantics and reconciliation |
| Product email sending | BLOCKED | Entitlement, consent, private outbox, suppression and delivery gate exist; gate is deliberately disabled | Provider, verified sender domain, unsubscribe/preference center, bounce/complaint webhooks, worker secret, compliance evidence |
| Billing checkout | BLOCKED | Billing schema and safe-enable gate exist; `checkout_enabled=false` in production | Provider selection/configuration and every billing gate must pass before any checkout UI opens |
| Compliance/legal | BLOCKED | RESEARCH_ONLY/noindex, data-rights registry and formal checklist | Authorized Vietnamese legal/compliance approval |
| Ads first round | BLOCKED | Lookup, holding and history landings/events are implemented; spending not authorized | Production data/auth/measurement, six approved assets, compliance and account eligibility |

## Shipping conclusion

Operational static interface, strict HOSE-only licensed-bundle ingestion, fail-closed market-data publication gate, persistent account personalization, authenticated/rate-limited production API foundation, fail-closed email infrastructure and fail-closed billing foundation are implemented at their stated boundaries.

Any structurally valid three-letter ticker can enter the public lookup flow, but verified current-HOSE membership and real market conclusions remain gated. Live Top HOSE, production recommendations/performance, customer-facing DNSE-derived signals, actual product email sending, checkout and Ads remain **BLOCKED**.

Critical path: `licensed public/derived-data rights → supplier HOSE bundle → fresh production manifest → reconciliation/cache writer → enable authenticated API only after evidence → signed-in E2E/privacy drill → email/payment providers + webhooks → formal compliance → PRODUCTION_APPROVED`.
