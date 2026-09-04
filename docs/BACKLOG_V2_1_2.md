# StockRadar V2.1.2 Backlog

The implementation order follows the current conversion flow. Items outside it are intentionally deprioritized.

## Completed in the operational build

- Dynamic ticker lookup shell, master-driven autocomplete and honest fail-closed results.
- Four horizon freshness, new-position and holding views.
- Public lifecycle/P&L plus VN-Index benchmark contract.
- Review due date and immutable recommendation journal.
- Today Changes significant-event view.
- Three-group onboarding UI/preferences schema.
- Free 09:00 / Trial-Paid intraday email entitlement model, consent and public lead capture.
- Per-horizon report cache and hit/miss/stale/refresh contract.
- Ticker-level subscriber dedupe and active intraday-universe union.
- Search/conversion analytics vocabulary and server-side rate limiter.
- Supabase managed-auth foundation, profiles, preferences/watchlist persistence, account deletion and RLS.
- Authenticated Premium stock-report Edge Function with JWT verification, service-role-only private cache RPCs and per-user quotas.
- Private API request observability without JWT/IP/email/payload retention.
- Provider-neutral billing foundation with anti-replay events, 30-day entitlements and fail-closed checkout gate.
- Premium-interest fallback when payment collection is disabled.
- SSI raw market/OHLCV adapter and DataCore raw financial-statement adapter; provider scores/recommendations are excluded from the StockRadar engine.
- Automatic StockRadar research, valuation and scoring from raw inputs.
- GitHub Pages fail-closed build, regression checks, auth/public/buyer-ready verification and deployment pipeline.

## Remaining critical path

1. Contract and license a current HOSE security master plus price/OHLCV, corporate-action, benchmark, fundamentals and event data with explicit publication/redistribution/derived-data rights.
2. Deliver current supplier credentials and populate the Drive production folders with a reconciled raw bundle.
3. Reconcile the full HOSE universe and generate a Decision-Grade production snapshot/manifest and report batch.
4. Complete signed-in browser E2E for Free/Trial/Paid fixtures, recovery/delete flow and privacy-operations drill.
5. Connect a verified email provider/domain with unsubscribe, suppression, bounce/complaint webhooks and delivery evidence; only then enable sending.
6. Connect the payment provider with signed webhooks, reconciliation, refund/chargeback handling and tax/compliance approval; only then enable checkout.
7. Obtain formal Vietnamese legal/compliance approval for public data/research wording and activation evidence.
8. Run Ads-ready measurement/QA and account eligibility checks, then start paid acquisition only after the production data/auth/compliance gates are open.

## Explicitly not before evidence

Board/terminal, native app, forum/social, chart suite, newsfeed, large AI chatbot, portfolio NAV, commercial API and new indicators.
