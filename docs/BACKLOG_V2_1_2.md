# StockRadar V2.1.2 Backlog

The implementation order follows the current conversion flow. Items outside it are intentionally deprioritized.

## Completed in the research build

- Dynamic ticker lookup shell, master-driven autocomplete and honest partial results.
- Four horizon freshness, new-position and holding views.
- Public lifecycle/P&L plus VN-Index start/end demo fields.
- Review due date and immutable recommendation journal.
- Today Changes significant-event view.
- Three-group onboarding UI/preferences schema.
- Free/Trial/Paid email eligibility and watchlist-limit policy.
- Per-horizon report cache and hit/miss/stale/refresh contract.
- Ticker-level subscriber dedupe and active intraday-universe union.
- Search/conversion analytics vocabulary and local rate-limiter reference.

## Blocked critical path

1. Contract and license a current HOSE security master plus price, corporate-action, benchmark, fundamentals and event data.
2. Reconcile full universe and populate a Decision Grade light snapshot.
3. Deploy authenticated API, durable cache, job queue, server-side throttling/rate limits and observability.
4. Implement managed auth, verification, privacy operations and watchlist/preferences persistence.
5. Connect verified Trial/Paid email with unsubscribe, suppression, bounce/complaint and delivery evidence.
6. Complete billing/reconciliation and formal Vietnamese compliance approval.
7. Run Ads-ready measurement/QA, then only the three approved landing propositions.

## Explicitly not before evidence

Board/terminal, native app, forum/social, chart suite, newsfeed, large AI chatbot, portfolio NAV, commercial API and new indicators.
