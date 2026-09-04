# StockRadar Authenticated Production API Gateway

Decision: production dynamic stock-report data is **authenticated-only**. Anonymous visitors receive the static/public surface; real dynamic data for eligible accounts goes through the Supabase Edge Function `stock-api`.

This removes the need to expose the licensed production cache directly through GitHub Pages or the public Supabase Data API.

## Request path

`Browser with Supabase session → stock-api (JWT required) → account/tier gate → per-user quota RPC → private report-cache RPC → private request audit → response`

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

A later `granted=false` event for DATA_RIGHTS or COMPLIANCE on the currently active manifest/snapshot automatically closes the API in the **same transaction**, clears the active bindings and writes a `DISABLE` audit event with `AUTO_REVOKE` evidence. This prevents rights/compliance revocation from depending on a later worker run or deployment.

`deactivate_stockradar_api(...)` also supports deliberate operational shutdown, clears active gate bindings and writes a `DISABLE` audit record. Approval and activation history is not rewritten.

Approval recording, activation and deactivation share a PostgreSQL advisory lock so a concurrent grant/revocation cannot race an activation decision.

All approval/activation functions are `SECURITY DEFINER`, use an empty `search_path`, and are executable only by `service_role`. Browser roles receive no table or RPC access.

## Data isolation

The following objects stay in the `private` schema and have no browser grants:

- `stock_api_gate`;
- `stock_report_cache`;
- `stock_api_rate_limit_policies`;
- `stock_api_rate_limit_windows`;
- `stock_api_approval_events`;
- `stock_api_activation_events`;
- `stock_api_request_events`.

The public-schema report/quota/cache-write/activation/audit RPCs are not browser APIs. Execute privilege is revoked from `public`, `anon` and `authenticated`, and granted only to `service_role` where applicable. The browser therefore cannot bypass the Edge Function by calling private runtime functions directly.

## Rate limit

Initial server-side safety caps for the `stock_report` bucket are configuration values, not product promises:

- Free: 30 requests / 60 seconds;
- Trial: 90 requests / 60 seconds;
- Paid: 180 requests / 60 seconds.

The limiter reads `account_tier` and `account_status` from `public.profiles`; inactive accounts are denied. A PostgreSQL advisory lock serializes concurrent requests per user/bucket. The Edge Function returns rate-limit headers and HTTP 429 with `Retry-After` when the quota is exhausted.

The current report route itself is Premium-only (`TRIAL`/`PAID`); the Free quota remains a configuration-ready safety policy for any future authenticated Free route.

These caps should be tuned from observed legitimate traffic before production launch.

## Request observability

Migration `20260904042030_add_stock_api_request_observability` adds private, authenticated-request operational telemetry.

For requests where a valid Supabase user has already been resolved, the Edge Function records only:

- `user_id`;
- account tier at request time;
- valid ticker/horizon when present;
- normalized outcome/reason;
- HTTP status;
- request latency in milliseconds;
- rate-limit remaining when available;
- timestamp.

The audit intentionally **does not store JWT/Authorization headers, email, IP address, user-agent, request body or report payload**.

`private.stock_api_request_events` has RLS enabled and no direct grants to `anon`, `authenticated` or `service_role`. Inserts are only available through `record_stockradar_api_request_event(...)`, a `SECURITY DEFINER` RPC executable only by `service_role`. Audit failure is non-fatal to the customer response and is logged only as a generic server-side error code.

Operational outcomes include invalid request, inactive account, Premium required, rate-limited, quota/report RPC failure, blocked data gate, not found and ready. This gives StockRadar enough evidence to tune quotas and investigate failures without turning observability into a second store of sensitive request data.

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

Edge Function `stock-api`: deployed and ACTIVE, **version 3**, with JWT verification and authenticated request observability.

Production API gate: **disabled**. Production stock-report cache rows: 0. Request audit rows: 0 at the 2026-09-04 post-deploy verification because no authenticated production report request has been generated in this deployment session.

This is intentional. Licensed HOSE production data, redistribution/derived-data rights and compliance approval are not yet present. Deployment of the gateway, cache publisher, audit layer or browser client does not open production market data.
