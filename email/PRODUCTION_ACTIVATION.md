# StockRadar Premium Email — Production Activation Runbook

This runbook is operational. It does **not** authorize delivery by itself.

## 0. Product contract

- Free receives only necessary account/transactional email.
- `DAILY_BRIEF`, `EVENT_ALERT`, `POST_SESSION_DIGEST`, and `WEEKLY_REPORT` are Trial/Paid product email.
- Product email requires verified email, current explicit consent, selected preference, no suppression, and the audited delivery gate.
- No material state change = no Action Alert.
- Never fabricate a ticker decision, price, performance result, provider success, or approval evidence for a canary.

## 1. Preflight before touching provider configuration

Run the private readiness RPC as an authorized operator/service:

`public.get_stockradar_email_runtime_readiness_v1()`

Expected before provider setup:

- `ready_to_activate = false`
- `ready_to_send_now = false`
- `sending_enabled = false`
- scheduler configured but disabled
- outbox contains no unexpected stale PROCESSING rows.

Resolve any operational blocker unrelated to provider evidence before continuing.

## 2. Configure real provider secrets

Use the Supabase secret manager / Edge Function environment. Never commit values to GitHub, migration SQL, documentation, issue comments, CI logs, or browser code.

Required for Resend runtime:

- `RESEND_API_KEY`
- `STOCKRADAR_EMAIL_FROM`
- `RESEND_WEBHOOK_SECRET`

Recommended:

- `STOCKRADAR_EMAIL_REPLY_TO`
- `STOCKRADAR_PUBLIC_BASE_URL=https://stockradar.vn`
- `STOCKRADAR_FUNCTIONS_BASE_URL=<actual Edge Functions base>` when using a custom functions domain.

Supabase admin RPC calls in email functions prefer the current secret API key environment (`SUPABASE_SECRET_KEYS['default']`) and retain legacy service-role fallback only for compatibility.

Do not expose any of these values to the public website.

## 3. Verify sender domain

In the provider console:

1. Add the StockRadar sender domain/subdomain selected for product email.
2. Publish the exact DNS records supplied by the provider.
3. Wait for the provider to mark sender/domain verification successful.
4. Confirm `STOCKRADAR_EMAIL_FROM` uses a verified sender identity.
5. Save an evidence reference that another operator can inspect later. Do not put secret material in the evidence reference.

Do not record `SENDER_DOMAIN` approval before provider verification is actually complete.

## 4. Configure and verify delivery webhook

Webhook endpoint:

`<functions-base>/email-webhook`

Requirements:

- provider webhook signing secret is stored as `RESEND_WEBHOOK_SECRET`;
- source events reach the endpoint;
- raw-body signature verification succeeds;
- replay tolerance works;
- duplicate provider event IDs remain idempotent;
- bounce and complaint events create suppression instead of repeatedly retrying a recipient.

Record only non-secret evidence references.

## 5. Canary account

Use a real internal Trial/Paid StockRadar account with:

- verified email;
- current consent;
- at least one intentionally selected Premium email product;
- a small watchlist;
- no fabricated recommendation or fabricated performance result.

If no real eligible stock decision exists, test delivery with a non-decision operational/canary payload through a separately approved safe procedure. Never generate a fake BUY/SELL just to test email rendering.

## 6. Unsubscribe canary

Before activation evidence is granted:

1. Send an authorized real canary through the actual provider path.
2. Confirm `List-Unsubscribe` and One-Click headers are present.
3. Confirm per-product unsubscribe disables only that selected product.
4. Confirm ALL unsubscribe disables product email, records current consent withdrawal/suppression as designed, and does not delete the StockRadar account/watchlist.
5. Confirm a claimed-but-not-yet-sent email is suppressed by final preflight after unsubscribe.

Only then may `UNSUBSCRIBE` evidence be approved.

## 7. Bounce / complaint canary

Use the provider's documented safe testing method where available.

Confirm:

- webhook signature validation succeeds;
- delivery audit receives the event once;
- bounce/complaint creates an active suppression;
- product-email preference is disabled;
- future enqueue/claim/preflight refuses delivery to that user;
- no raw provider webhook body or recipient content is exposed publicly.

Only then may `BOUNCE_COMPLAINT` evidence be approved.

## 8. Compliance approval

Before product-email delivery is enabled, confirm at minimum:

- current consent wording/version matches production UI/database;
- privacy page accurately describes product-email interest/retention and delivery behavior;
- unsubscribe is usable without account deletion;
- no product email is enabled for Free;
- suppression/bounce/complaint handling is operational;
- no advertiser or third party receives conversation/account data through this email runtime;
- legal/privacy review appropriate for the intended Vietnam operation is recorded.

Only then may `COMPLIANCE` evidence be approved.

## 9. Record the five approvals

Record real, current evidence with the service-role-only RPC:

`public.record_stockradar_email_delivery_approval_v1(...)`

Required approval types for the selected provider:

1. `PROVIDER_CONFIG`
2. `SENDER_DOMAIN`
3. `UNSUBSCRIBE`
4. `BOUNCE_COMPLAINT`
5. `COMPLIANCE`

Never create placeholder or guessed approvals.

## 10. Readiness gate

Call:

`public.get_stockradar_email_runtime_readiness_v1()`

Activation is allowed only when:

- `ready_to_activate = true`
- `blockers = []`
- scheduler configured
- cron active with expected schedule
- no stale PROCESSING outbox rows
- all five current approvals are true for the selected provider.

If any blocker remains, stop.

## 11. Deliberate activation

Call the service-role-only activation RPC with a real activation evidence reference:

`public.activate_stockradar_email_delivery_v1(<provider>, <evidence_ref>)`

Successful activation must:

- set `sending_enabled = true` through the audited RPC only;
- audit an ENABLE event;
- automatically enable the Vault-backed email scheduler;
- leave direct service-role UPDATE on the delivery gate unavailable.

Then immediately call readiness again. `ready_to_send_now` should only be true when both delivery and scheduler are active.

## 12. First live delivery window

For the first production window:

- keep recipient scope intentionally small;
- monitor outbox PENDING/PROCESSING/FAILED/SUPPRESSED/SENT counts;
- inspect delivery webhook events;
- verify actual inbox arrival latency from scheduled/evaluated time;
- verify email and website state agree;
- verify no duplicate email from retries;
- verify late-open and no-chase copy where relevant;
- verify no Action Alert appears when state did not materially change.

Do not broaden rollout until this window is clean.

## 13. Emergency stop

If there is any material integrity, provider, consent, delivery, or data problem, call:

`public.deactivate_stockradar_email_delivery_v1(<evidence_ref>)`

Expected result:

- `sending_enabled = false`;
- scheduler is disabled automatically;
- new claims stop;
- final preflight suppresses rows that became ineligible;
- DISABLE event is audited.

Revoking any current approval also auto-disables delivery.

## 14. Ongoing monitoring

Monitor at least:

- outbox failure rate;
- stale PROCESSING rows;
- provider delivery latency;
- bounce and complaint rate;
- unsubscribe rate by product;
- Action Alert open/click behavior;
- percentage of paid users with active watchlist and alert-enabled tickers;
- paid renewal for users who actually received relevant alerts.

Do not optimize for raw email volume. The product metric is whether StockRadar reliably reduces the user's need to manually monitor their own tickers.
