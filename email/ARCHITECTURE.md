# StockRadar Premium Email Architecture

Status: **production runtime implemented, delivery intentionally OFF** until provider/domain/unsubscribe/bounce-compliance evidence is recorded and the audited activation gate is opened.

## Product principle

A paid user does not buy “more email”. They pay so StockRadar can **watch the tickers that matter to them and bring a meaningful decision change to their inbox**.

The product contract is therefore:

- **Free:** account/transactional email only when needed for signup, security, billing or account operations.
- **Trial/Paid:** may receive product email after verified email + explicit current consent + selected preference + no suppression + active delivery gate.
- **No material state change = no Action Alert.**
- Email never calculates a stock decision. It only renders a decision already confirmed by StockRadar’s engine/state machine.

## Product email types

| Type | Entitlement | Purpose |
| --- | --- | --- |
| `DAILY_BRIEF` | Trial/Paid | 09:00 watchlist-first morning command center. |
| `EVENT_ALERT` | Trial/Paid | Material state change at an eligible intraday checkpoint. |
| `POST_SESSION_DIGEST` | Trial/Paid, optional | End-of-session summary of meaningful changes. |
| `WEEKLY_REPORT` | Trial/Paid, optional | Weekly history/review. |

Free preferences can never become delivery entitlement for these four products.

## Premium Daily 09:00

Premium Daily is ordered around the recipient, not a generic market newsletter:

1. **Watchlist / owned tickers that changed** — urgent risk first.
2. **Stable monitored tickers** — explicit “no action needed” when useful.
3. **Market context** — short supporting context after the user’s tickers.
4. **Optional external opportunities** — secondary to the recipient’s own watchlist.
5. **Direct link to My StockRadar.**

Subject examples:

- `[StockRadar] 2 mã cần chú ý hôm nay · 04/09`
- `[StockRadar] Watchlist ổn định · chưa cần hành động · 04/09`

A daily report must remain skimmable before the session and must never fabricate activity to make Premium appear busy.

## Premium Action Alert

Every Action Alert follows this order:

1. **What changed?** — previous state → current state.
2. **If not owned:** new-position decision when supported.
3. **If owned:** holding decision when supported.
4. **Action map:** reference price, Buy Zone, Stop/invalidation, Target, Risk/Reward where required by the horizon.
5. **Why now?** — 2–4 strongest reasons only.
6. **What invalidates this?** — explicit condition.
7. **Next review / timestamp.**
8. **CTA:** `XEM TRẠNG THÁI MỚI NHẤT`.

Example subject:

`[StockRadar] HPG · CHỜ → MUA | 10:30`

For BUY/ADD, the email must warn that a late reader must not automatically chase price outside the action zone.

## Checkpoints and noise suppression

Scheduled intraday decision reviews are:

- 10:30
- 11:15
- 13:30
- 14:15

These are review checkpoints, not a promise of real-time-by-the-second delivery. If no eligible state transition occurs, no Action Alert is created.

Priority:

- **P0:** SELL / stop / invalidation / severe risk.
- **P1:** REDUCE / material risk deterioration.
- **P2:** BUY / ADD after full confirmation.
- **P3:** lower-urgency monitoring/digest content.

## One source of truth

The email path is strictly one-way:

`engine/state machine → premium email view-model → recipient-specific candidate → DB entitlement/gate → outbox → final preflight → provider worker`

Rules:

- `engine/stockradar/premium_email.py` validates/formats the Premium view-model.
- `engine/stockradar/email_orchestration.py` builds recipient-specific candidates with snapshot, decision reference, TTL, priority and deterministic idempotency key.
- The orchestration layer has no provider credential and does not make network calls.
- `EVENT_ALERT` cannot be created when previous state equals current state.
- Database eligibility is authoritative even if a browser/client preference is stale.

## Paid-only entitlement

Canonical source migration:

`supabase/migrations/20260904110500_assert_paid_only_product_email.sql`

A product email is eligible only when all relevant conditions are true:

- account is `ACTIVE`;
- tier is `TRIAL` or `PAID`;
- email is verified;
- the user selected the specific email product;
- the latest consent is granted and matches the current consent version;
- there is no active unsubscribe/bounce/complaint/security suppression;
- the audited delivery gate is enabled.

Account verification must not auto-enable product email for Free.

## Outbox runtime

Canonical runtime migration:

`supabase/migrations/20260904101500_add_email_delivery_runtime_v2.sql`

The private outbox supports:

- unique idempotency key;
- `scheduled_at` + `expires_at` TTL;
- priority;
- snapshot and decision reference;
- claim timestamp;
- bounded retry attempts;
- `PENDING / PROCESSING / SENT / FAILED / SUPPRESSED` lifecycle.

Workers claim rows with `FOR UPDATE ... SKIP LOCKED` so concurrent drains cannot intentionally claim the same row.

Expired or max-attempt rows are suppressed rather than sent late indefinitely.

## Final send preflight

Canonical migration:

`supabase/migrations/20260904103000_add_email_send_preflight.sql`

Immediately before a provider call, the worker rechecks:

- row is still PROCESSING;
- TTL has not expired;
- email is still verified;
- current entitlement still allows this email type;
- consent has not been withdrawn;
- suppression has not appeared;
- delivery gate is still open.

This closes the race where a user unsubscribes or an operator emergency-stops delivery after a row was claimed but before the provider request.

Invalid rows become `SUPPRESSED` and are not sent.

## Provider worker

Edge Function:

`supabase/functions/email-worker/index.ts`

Properties:

- provider implementation is Resend-compatible;
- provider API key and sender identity are environment secrets only;
- uses Resend `Idempotency-Key`;
- contains `List-Unsubscribe` and RFC-style One-Click headers;
- renders responsive HTML with decision-first content;
- uses separate website and Edge Function base URLs;
- can be called only by an internal service credential or the Vault-backed scheduler token;
- public unauthenticated calls are rejected before outbox/provider work.

Supabase admin credentials prefer the new `SUPABASE_SECRET_KEYS['default']` secret API key model, with legacy service-role fallback only while needed.

## Scheduler

Canonical migrations:

- `supabase/migrations/20260904104000_add_email_worker_scheduler.sql`
- `supabase/migrations/20260904104200_bind_email_scheduler_to_delivery_gate.sql`

Scheduler design:

- `pg_cron + pg_net`;
- a random 32-byte internal scheduler token is generated inside Postgres and stored only in Supabase Vault;
- database stores only its SHA-256 hash;
- cron schedule: `*/2 2-11 * * 1-5` (09:00–18:59 Vietnam time, Monday–Friday);
- dispatcher performs **no HTTP call** unless scheduler is enabled, delivery is enabled and at least one non-expired email is due;
- enabling delivery automatically requires a valid scheduler/Vault token and enables the scheduler;
- disabling delivery automatically disables scheduler dispatch.

The scheduler token is not a provider credential.

## Unsubscribe

Edge Function:

`supabase/functions/email-unsubscribe/index.ts`

Each product email can carry:

- unsubscribe for that email type;
- unsubscribe all product content.

Tokens are random, stored only as hashes in the database, expire, and are one-use. Unsubscribing product email does **not** delete the StockRadar account or watchlist.

One-click unsubscribe and account-center preferences must remain consistent.

## Delivery webhook and suppression

Edge Function:

`supabase/functions/email-webhook/index.ts`

Webhook requirements:

- raw body is verified before JSON parsing;
- Svix/Resend signing secret (`whsec_`) is required;
- HMAC-SHA256 signature check;
- short replay tolerance window;
- provider event IDs are idempotent;
- delivery audit stores operational metadata + body digest, not raw recipient content.

Bounce or complaint automatically creates a suppression and disables product-email preference for that user.

## Audited activation

Canonical migration:

`supabase/migrations/20260904102500_add_email_delivery_activation_audit.sql`

Direct service-role mutation of the delivery gate is revoked. Production activation requires current positive evidence for the selected provider:

1. `PROVIDER_CONFIG`
2. `SENDER_DOMAIN`
3. `UNSUBSCRIBE`
4. `BOUNCE_COMPLAINT`
5. `COMPLIANCE`

Only after all five current approvals exist may the service-role activation RPC set `sending_enabled=true`.

Revoking a current approval auto-disables delivery. Manual deactivation is also audited.

## Operational readiness

Private service-role-only RPC:

`public.get_stockradar_email_runtime_readiness_v1()`

Source migration:

`supabase/migrations/20260904111000_add_email_runtime_readiness.sql`

It reports, without PII or provider secrets:

- current candidate provider;
- approval readiness;
- delivery gate state;
- scheduler/cron state;
- outbox counts and stale processing;
- latest outbox error;
- activation/delivery audit counts;
- blockers;
- `ready_to_activate` and `ready_to_send_now`.

## Production activation rule

Do not open product-email delivery merely because code is deployed.

Actual sending remains OFF until all of the following are proven with real evidence:

- provider API credential configured in Supabase secrets;
- verified StockRadar sender domain/DNS;
- sender address configured;
- webhook signing secret configured;
- provider webhook points to the StockRadar webhook endpoint;
- real one-click unsubscribe test succeeds;
- real bounce/complaint test succeeds;
- privacy/compliance approval is current;
- readiness RPC has no activation blockers;
- an operator records approval events and deliberately calls the activation RPC.

Until then, `sending_enabled=false` and no paid email promise may be treated as operational delivery.
