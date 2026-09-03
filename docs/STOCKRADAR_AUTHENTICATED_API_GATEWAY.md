# StockRadar Authenticated Production API Gateway

Decision: production dynamic stock-report data is **authenticated-only**. Anonymous visitors receive the static/public surface; real dynamic data for Free, Trial and Paid accounts goes through the Supabase Edge Function `stock-api`.

This removes the need to expose the licensed production cache directly through GitHub Pages or the public Supabase Data API.

## Request path

`Browser with Supabase session → stock-api (JWT required) → per-user quota RPC → private report-cache RPC → response`

The Edge Function is deployed with Supabase JWT verification enabled. It also resolves the user again with Supabase Auth before any service-role RPC is called.

## Fail-closed gates

`private.stock_api_gate.api_enabled` defaults to false and cannot become true unless:

- production data is ready;
- data/public-derived rights are approved;
- compliance is approved;
- an evidence reference is recorded.

When disabled, report retrieval returns `BLOCKED_DATA_GATE / PRODUCTION_API_DISABLED`. Expired cache rows return `BLOCKED_DATA_GATE / REPORT_STALE`.

## Data isolation

The following objects stay in the `private` schema and have no browser grants:

- `stock_api_gate`;
- `stock_report_cache`;
- `stock_api_rate_limit_policies`;
- `stock_api_rate_limit_windows`.

The only public-schema RPCs are `consume_stockradar_api_quota` and `fetch_stockradar_cached_report`. Execute privilege is revoked from `public`, `anon` and `authenticated`, and granted only to `service_role`. The browser therefore cannot bypass the Edge Function by calling the RPC directly.

## Rate limit

Initial server-side safety caps for the `stock_report` bucket are configuration values, not product promises:

- Free: 30 requests / 60 seconds;
- Trial: 90 requests / 60 seconds;
- Paid: 180 requests / 60 seconds.

The limiter reads `account_tier` and `account_status` from `public.profiles`; inactive accounts are denied. A PostgreSQL advisory lock serializes concurrent requests per user/bucket. The Edge Function returns rate-limit headers and HTTP 429 with `Retry-After` when the quota is exhausted.

These caps should be tuned from observed legitimate traffic before production launch.

## Browser boundary

Allowed browser origins are restricted to:

- `https://stockradar.vn`;
- `https://www.stockradar.vn`;
- `https://nguyenlinhns-arch.github.io`;
- local development origins on port 8000.

Ticker input is exactly three ASCII letters and horizon is one of `SHORT_TERM`, `MEDIUM_TERM`, `LONG_TERM`, `ACCUMULATION`.

Responses use `Cache-Control: no-store`; authorization tokens are never logged or returned.

## Current state

Edge Function `stock-api`: deployed and ACTIVE with JWT verification.

Production API gate: **disabled** because licensed HOSE production data, redistribution/derived-data rights and compliance approval are not yet present.

This is intentional. Deployment of the gateway does not open production market data.
