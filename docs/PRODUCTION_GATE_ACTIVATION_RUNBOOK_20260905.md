# StockRadar Production Gate Activation Runbook — 2026-09-05

## Principle

Fail closed. Do not enable public action reports or outbound product email until the relevant external evidence and technical checks pass.

## Current capabilities

- Internal Research AI: operational on fresh internal research cache.
- Public Action API: blocked pending DATA_RIGHTS + COMPLIANCE approval evidence and fresh manifest-bound reports.
- Product email: sending-only credential is stored in Vault and the worker health check confirms provider/sender configuration. Delivery remains disabled pending Resend DKIM verification and delivery/compliance gate activation. No product email has been sent.
- Email webhook: deployed; signing secret is stored in Supabase Vault and the function can fall back to Vault.

## Implementation update — 5 September 2026

- Single-stock AI answers retain four layers: 4M (business), CANSLIM (growth), SEPA/VCP (technical structure), and VPA (price/volume). Missing qualitative or financial evidence is stated explicitly.
- Four investment horizons are Short term, 3–6 months, 12 months, and Accumulation. Short-term evidence includes observed moving averages, price structure, the watched breakout level, volume comparisons, cloud/band observations when present, and reassessment conditions. The client copy guard preserves method names inside the AI conversation.
- Legacy historical-multiple values are no longer automatically assigned to 3–6-month and 12-month forecasts. For example, ACB's former 24,116.965 VND value was 20% × EPS 3,730.45 × historical P/E 7.04 + 80% × book value 17,796.69 × historical P/B 1.325. This calculation had no verified time-specific forecast assumptions. The API removes unverified price forecasts from research responses; the next research build requires separate verified forecasts for each horizon.
- The homepage reads a public allowlist of current, approved reports and an operational summary. It distinguishes no qualifying stocks, stale data, publication pending, and a request failure. At the checked snapshot: 405 HOSE stocks, five initial price/volume patterns, zero qualified buy candidates. Price date: 4 September; review completed 08:28:32 Vietnam time on 5 September.
- Dates and times use Asia/Ho_Chi_Minh. The next planned review is 08:10 on 7 September, and the daily bulletin is planned at 09:00. These are weekday schedules, not an exchange-holiday calendar. Existing intraday alert processing is scheduled at 10:35, 11:20, 13:35, and 14:20, after the respective scans. The worker checks its queue every two minutes when enabled; schedules do not prove delivery.
- The daily producer only queues opted-in eligible accounts and uses the same released reports as the homepage. Date/recipient deduplication, expiry, approval/report rechecks, unsubscribe, and suppression are enforced before provider submission. Public SENT timestamps mean provider acceptance, not confirmed inbox delivery.
- DNS is configured at Mat Bao. Resend has verified the return-path MX and SPF TXT; DKIM remains pending even though authoritative DNS matches the published key. Never store a provider API token in this document or source control.

Validation: Python/Node regressions; production Pages build; desktop/mobile recommendation states; authenticated live ACB response; transaction-rolled-back SQL tests in `supabase/tests/recommendation_email_status.sql`. SQL fixtures never dispatch email or persist simulated approvals.

## Gate A — DATA_RIGHTS

Required evidence:

1. Written commercial agreement or written provider approval that explicitly covers StockRadar.vn.
2. Public/paid-user display rights.
3. Derived-data rights for rankings, scores, signals, buy zones, stop/target, research recommendations and email alerts.
4. Cache/retention rights and permitted refresh frequency.
5. Territory, attribution and redistribution restrictions.
6. Dataset scope: HOSE universe, intraday/EOD OHLCV, corporate actions, fundamentals and any market/flow layers used by Action Reports.

Do not infer rights from public accessibility, API access or a consumer subscription.

When evidence is received:

- Record immutable evidence reference.
- Build a licensed production manifest with a sha256 manifest reference.
- Publish fresh manifest-bound reports to private.stock_report_cache.
- Record DATA_RIGHTS approval via record_stockradar_api_approval only after reviewer confirmation.

## Gate B — COMPLIANCE

Required evidence:

1. Named Vietnamese legal/compliance reviewer.
2. Reviewed product scope and artifact/version references.
3. Written conclusion on research/education vs regulated securities-investment advisory boundaries.
4. Conditions for paid alerts, watchlist/personalization, buy zone/stop/target/RR outputs, marketing claims and track record.
5. Required disclaimers, terms, consent, billing/refund, privacy and complaint/correction process.
6. Review/expiry date and unresolved conditions.

When evidence is received:

- Implement every stated condition before approval.
- Record COMPLIANCE approval against the same manifest_ref + snapshot_id as DATA_RIGHTS.

## Gate C — PUBLIC ACTION API

Activation prerequisites enforced by database:

- current DATA_RIGHTS approval = true;
- current COMPLIANCE approval = true;
- at least one fresh report bound to the approved manifest and snapshot;
- production report payload must be DECISION_GRADE and public_release_allowed=true;
- action contract must remain fail-closed.

Activation:

- call activate_stockradar_api(manifest_ref, snapshot_id, evidence_ref);
- verify runtime health returns public_action=READY;
- run regression and one non-action + one action test before exposing UI.

## Gate D — RESEND DOMAIN

Required DNS records for stockradar.vn (values are maintained in the Resend domain configuration):

- DKIM TXT at resend._domainkey;
- Return-Path MX at send;
- SPF TXT at send.

Do not mark sender_domain_verified until Resend reports VERIFIED.

After verification:

1. Confirm sending-only API key exists and is restricted to stockradar.vn.
2. Store the key only in Supabase Edge Secrets/Vault; never GitHub or migration SQL.
3. Configure a sender such as alerts@stockradar.vn only after domain verification.
4. Confirm unsubscribe, bounce/complaint and suppression handling.
5. Send a transactional test to an authorized internal mailbox.
6. Confirm webhook delivery events are written to private.email_delivery_events.

## Gate E — EMAIL DELIVERY

Only enable sending when all are true:

- provider_configured;
- sender_domain_verified;
- unsubscribe_ready;
- bounce_complaint_ready;
- compliance_approved;
- sending credential present;
- worker preflight passes.

Then enable scheduler, send a test, verify SENT -> DELIVERED, and only then set sending_enabled=true for product mail.

## Monitoring

Runtime health must expose independently:

- research_ai;
- public_action;
- email_delivery;
- email_scheduler;
- cache freshness/contamination;
- outbox queue/failures;
- notification/action-event activity.

No gate may be promoted based on verbal assumptions or stale evidence.
