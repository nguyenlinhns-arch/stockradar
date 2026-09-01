# STOCKRADAR BUILD STATUS V2

Updated: 2026-09-01 UTC. Allowed states: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `TESTING`, `PASS`, `FAILED`.

| Workstream | Status | Evidence | Remaining production gate |
| --- | --- | --- | --- |
| V2 product contract | PASS | `STOCKRADAR_PRODUCT_SPEC_V2.md` plus the eleven required lifecycle/performance/rights/email/subscription/analytics/ads/compliance specs | Validate with real users without widening claims |
| Four horizon scoring | PASS | Distinct 100-point profiles and anti-double-count/probability tests | Licensed data and horizon-matched OOS calibration |
| Recommendation Gate | PASS | Ranking is separated from publish eligibility; extension/data/market/liquidity/event/evidence/horizon gates tested | Calibrate thresholds on approved HOSE dataset |
| Publication/activation lifecycle | PASS | Deterministic first eligible post-publication zone-touch; unactivated has no entry/P&L | Production timestamp/bar specification and exchange calendar |
| Performance/corporate action | PASS | Open/final/excess return implementation; split/cash handling; unresolved rights blocks; closed result frozen | Approved corporate-action and benchmark provider |
| Append-only track record | PASS | Immutable recommendations/events/corrections/manual overrides in SQLite; mutation tests pass | Production database, access control, backups and monitoring |
| Website V2 | PASS | Home public search/proof, recommendation filters, Performance, nine-question report, sector/Knowledge/email/account/pricing; 23 routes | Live market adapter and production services |
| Static GitHub Pages | PASS | Core commit `020f22c393c606353319de295ed26ed7af419e6c`; workflow `33526215030` SUCCESS; 23/23 public routes checked; MOCK/SHADOW/noindex/no-write | None for research demo; not a production backend |
| Automated regression | PASS | 57/57 tests; JS syntax; CSS brace parity; static build | Add production adapter and end-to-end service tests |
| Live browser QA | PASS | Home, lifecycle filter, Performance and DEMO1 interaction checked; no page overflow at desktop viewport; only browser-extension-origin metadata errors observed | Real-device/mobile visual matrix before production launch |
| GPT client V2 | PASS | Nine-question explanation, recommendation/activation/performance/mode rules and six new regressions | HTTPS authenticated read API/Action |
| Analytics V2 | PASS | Canonical event schema/client/server allowlist and privacy rules | Production first-party store, identity/dedup and consent controls |
| Email architecture | PASS | Pre-session primary email, event/post-session/weekly contracts and scan checkpoints | Sender/provider, consent, unsubscribe, bounce/complaint and worker — BLOCKED |
| Auth/watchlist | BLOCKED | Minimal schemas and honest unavailable UI | Managed auth, secure production DB, threat model and privacy operations |
| Billing/subscription | BLOCKED | Free/Advanced entitlements and exact 30-day grant contract; 199k/299k hypotheses | Provider/webhooks, reconciliation, tax/refund/security/compliance |
| Full HOSE data/rights | BLOCKED | Rights registry/provenance/fail-closed contract | Licensed current data, redistribution/derived-data approval and reconciliation |
| Compliance/legal | BLOCKED | RESEARCH_ONLY mode and formal review checklist | Authorized Vietnamese legal/compliance approval and documented conditions |
| Ads first round | BLOCKED | V2 propositions, equal-budget plan and copy draft; old Breakout/Risk retired from first round | Six new approved assets, production events, data rights, compliance and account eligibility |
| Custom domain/brand | BLOCKED | Pages URL works; brand boundary documented | Domain ownership/DNS/HTTPS and trademark/confusion clearance |

## Shipping conclusion

Research-only V2 demo: **PASS**.

Production StockRadar, live Top HOSE, production recommendations/performance, email delivery, paid Advanced and Ads: **BLOCKED**.

Critical path: `licensed data/rights → full-universe reconciliation → four-horizon calibration → forward SHADOW history → secure auth/email/billing/privacy → formal compliance → PRODUCTION_APPROVED`.
