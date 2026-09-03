# StockRadar Ticker Lookup and Cache Specification V2.1.2

## Contract

Normalize submitted ticker to uppercase and validate it against the current licensed HOSE security master before any production conclusion. Autocomplete may use a verified master only; it never runs deep analysis while typing. Unknown/non-HOSE values do not generate a production report or silently move to another exchange.

Until the licensed security master is approved, the public UI may accept a structurally valid three-letter ticker for navigation, but that does **not** assert current HOSE membership.

## Three layers

1. Full-HOSE light snapshot for Top/sector claims and quick public fields.
2. On-demand deep analysis for searched, ranked, recommended or popular/watchlisted tickers.
3. Deduplicated intraday active universe for recommendations, near-trigger candidates and Trial/Paid watchlists.

On-demand popularity cannot redefine the universe used by Top ranking.

## Production cache

The production key is ticker + horizon. Every row stores snapshot ID, generation/expiry times, Decision-Grade report payload and exact SHA-256 manifest reference.

A report may be served only when:

- the report payload passes `STOCKRADAR_REPORT_PAYLOAD_CONTRACT.md`;
- the row is not expired;
- its snapshot ID matches `private.stock_api_gate.active_snapshot_id`;
- its manifest reference matches `private.stock_api_gate.active_manifest_ref`;
- data, rights and compliance gates are all approved;
- `api_enabled=true` has been deliberately opened.

A stale or mismatched report fails closed. A miss does not trigger an unbounded browser-side analysis job.

## Authenticated dynamic API

Customer-facing dynamic production reports use:

`browser session → Supabase Edge Function stock-api → server-side quota → private cache`

The Edge Function requires a valid Supabase JWT. The browser never receives service-role credentials and cannot call the private cache or service-role-only RPCs directly.

Initial safety limits for the `stock_report` bucket are configurable server-side values, not commercial promises:

- Free: 30 requests / 60 seconds;
- Trial: 90 requests / 60 seconds;
- Paid: 180 requests / 60 seconds.

Inactive accounts are denied. HTTP 429 includes `Retry-After`.

Anonymous users do not receive the dynamic licensed production API. They use the static/public surface on GitHub Pages. This avoids pretending that GitHub Pages can enforce server-side rate limits or protect a licensed cache.

## Browser behavior

The stock-report page attempts the authenticated API only when a signed-in session exists. It replaces the static fail-closed surface **only** when the API returns `READY`.

401/403/404/5xx, closed Data Gate, stale/mismatched cache or other non-ready responses leave the static surface unchanged. A rate-limit response may show a temporary quota message to the signed-in user.

The UI supports four independent horizons: Short, Medium, Long and Accumulation. It displays model probability only when the payload explicitly carries valid calibration evidence; score is never rendered as probability.

## Failure and cost controls

Do not promise background completion without a real queue. Production still requires licensed data ingestion, reconciliation, cache population, observability and controlled refresh workers. Material events must invalidate affected cache rows regardless of nominal TTL.
