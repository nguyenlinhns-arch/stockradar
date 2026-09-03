# StockRadar Authenticated Production API Gateway

Decision: production dynamic stock-report data is **authenticated-only**. Anonymous visitors receive the static/public surface; real dynamic data for Free, Trial and Paid accounts goes through the Supabase Edge Function `stock-api`.

This removes the need to expose the licensed production cache directly through GitHub Pages or the public Supabase Data API.

## Request path

`Browser with Supabase session → stock-api (JWT required) → per-user quota RPC → private report-cache RPC → response`

The Edge Function is deployed with Supabase JWT verification enabled. It also resolves the user again with Supabase Auth before any service-role RPC is called.

## Fail-closed gates

`private.stock_api_gate.api_enabled` defaults to false. The safe-enable constraint requires:

- production data is ready;
- data/public-derived rights are approved;
- compliance is approved;
- an activation evidence reference is recorded;
- an active manifest SHA-256 reference is recorded;
- an active snapshot ID is recorded.

When disabled, report retrieval returns `BLOCKED_DATA_GATE / PRODUCTION_API_DISABLED`. Expired cache rows return `BLOCKED_DATA_GATE / REPORT_STALE`. A row bound to another manifest or snapshot returns `BLOCKED_DATA_GATE / CACHE_MANIFEST_MISMATCH`.

## Audited activation procedure

A normal production operator must not enable the API by editing gate columns directly.

Approvals are append-only events in `private.stock_api_approval_events` and are scoped to an exact manifest SHA-256 + snapshot ID. Supported approval types are:

- `DATA_RIGHTS`;
- `COMPLIANCE`.

`record_stockradar_api_approval(...)` records a grant or revocation with an evidence reference. The latest event for each approval type is authoritative.

`activate_stockradar_api(...)` is service-role-only and refuses activation unless:

1. the manifest reference has the `sha256:<64 hex>` form;
2. the latest DATA_RIGHTS approval for that exact manifest/snapshot is `granted=true`;
3. the latest COMPLIANCE approval for that exact manifest/snapshot is `granted=true`;
4. at least one unexpired report already exists in the private cache for that exact manifest/snapshot;
5. activation evidence is recorded.

Successful activation sets the exact active manifest/snapshot and writes an `ENABLE` audit record to `private.stock_api_activation_events`.

`deactivate_stockradar_api(...)` closes the API, clears active gate bindings and writes a `DISABLE` audit record. Approval and activation history is not rewritten.

All approval/activation functions are `SECURITY DEFINER`, use an empty `search_path`, and are executable only by `service_role`. Browser roles receive no table or RPC access.

## Data isolation

The following objects stay in the `private` schema and have no browser grants:

- `stock_api_gate`;
- `stock_report_cache`;
- `stock_api_rate_limit_policies`;
- `stock_api_rate_limit_windows`;
- `stock_api_approval_events`;
- `stock_api_activation_events`.

The public-schema report/quota/cache-write/activation RPCs are not browser APIs. Execute privilege is revoked from `public`, `anon` and `authenticated`, and granted only to `service_role` where applicable. The browser therefore cannot bypass the Edge Function by calling private runtime functions directly.

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

The stock page keeps its static fail-closed surface for every non-READY response. A live authenticated report replaces that surface only after the gateway returns `READY`.

## Current state

Edge Function `stock-api`: deployed and ACTIVE with JWT verification.

Production API gate: **disabled**. Approval events: 0. Activation events: 0. Production stock-report cache rows: 0 at the latest 2026-09-03 verification.

This is intentional. Licensed HOSE production data, redistribution/derived-data rights and compliance approval are not yet present. Deployment of the gateway, cache publisher or browser client does not open production market data.
