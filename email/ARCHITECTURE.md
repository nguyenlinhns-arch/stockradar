# Email Architecture Contract

Status: signup/consent and pre-auth interest capture foundations implemented; no production sender is connected.

## Entitlement gate

Transactional mail is available where required for every account tier.

Product email is split by entitlement:

- `daily` Free brief: eligible only for a verified, explicitly consented Free/Trial/Paid account with the daily preference enabled. Free content is market-wide/basic and must not expose Premium buy/sell-map detail.
- Premium `daily`: Trial/Paid only after verification and explicit product consent.
- `state_change` / buy-sell event alerts: Trial/Paid only after verification and explicit product consent.
- `post_session` and `weekly`: Trial/Paid only unless a future spec explicitly defines a Free variant.

A Free user may retain interest in Premium-only alert preferences, but this is **preference data, not delivery entitlement**. The private eligibility layer must mask Premium-only products until the tier is Trial/Paid. Paid content is ordered by that recipient's own watchlist ticker, preferred horizon and sector before general items.

## Pre-auth email interest path

While production Auth SMTP remains closed, the public homepage may collect a minimal pending registration request without pretending that signup or delivery is complete.

1. The visitor enters an email and explicitly selects `DAILY_BRIEF`, `EVENT_ALERT`, or both. Nothing is pre-checked.
2. The visitor explicitly accepts the current privacy/consent version.
3. GitHub Pages calls the public `email-interest` Edge Function. The browser receives no service-role/provider secret.
4. The Edge Function enforces allowed origins, JSON/body limits, a honeypot and a daily-hashed technical request fingerprint for rate limiting.
5. Only the Edge Function's service role may invoke `public.capture_email_subscription_interest`; `anon` and `authenticated` have no direct execute grant.
6. The request is stored in `private.email_subscription_intents` as `PENDING_VERIFICATION` for at most 30 days. It is **interest only** and never authorizes delivery.
7. Premium-alert interest from this queue never bypasses Trial/Paid entitlement. Actual delivery still requires normal email verification, consent, suppression checks, product entitlement and the delivery gate.

This queue is intentionally separate from `public.product_email_preferences` and `private.product_email_eligibility`. A future verification/claim flow may reconcile a pending request only after control of the email address has been proven.

## Delivery windows

| Window | Purpose | Default content |
| --- | --- | --- |
| 09:00 Vietnam time | Daily pre-session report | explicit report date/data cutoff, market state, objective Top 5 HOSE when the full-universe gate passes, objective sector view, existing lifecycle changes and known event risks; Free/Premium depth follows entitlement |
| 10:30 / 11:15 / 13:30 / 14:15 | Confirmed state changes | Premium only: P0 risk/invalidation, then P1 readiness/trigger |
| After session | Freeze the close | Premium snapshot summary, new/changed/expired recommendations |
| Weekly | Review process | Premium state transitions, immutable outcomes and method note |

These are scheduled scans, not realtime-by-the-second promises. A scan may produce no email.

## Date and freshness contract

Every product email carries separate fields for:

- `report_date`: Vietnam calendar date of the email/report;
- `market_session_reference`: trading session represented by the primary market data;
- `data_cutoff_at`: latest verified source/snapshot time or strongest verified session boundary;
- `generated_at`: generation time in Vietnam time.

The daily subject must include `report_date`, for example:

`[StockRadar][dd/mm/yyyy] Báo cáo thị trường hàng ngày`

At 09:00, the latest verified data may still be from the previous trading session. In that case the email must show both dates explicitly and must not label the older snapshot as current-day market data.

For in-session action alerts, use the Vietnam signal date in the subject, for example:

- `[CHỨNG KHOÁN][dd/mm/yyyy] ĐẠT ĐIỂM MUA – <MÃ>`
- `[CHỨNG KHOÁN][dd/mm/yyyy] CẢNH BÁO BÁN – <MÃ>`

Corrections preserve the original report date but prepend `[CẬP NHẬT]` or `[ĐÍNH CHÍNH]` and expose the new generation/data cutoff time.

## Required event

Every candidate email event contains:

- `operation_id` and deterministic `idempotency_key`;
- `recommendation_id`, `snapshot_id`, ticker and horizon where applicable;
- previous/current internal state plus approved public label;
- event priority and reason;
- Data Grade, source time, detected time and validity boundary;
- `report_date`, `market_session_reference`, `data_cutoff_at`, `generated_at`;
- recipient tier, preference/consent version and effective product entitlement;
- confirmation, debounce and cooldown results.

Suggested idempotency key:

`sha256(user_id | recommendation_id | snapshot_id | to_state | event_type)`

The delivery worker may retry the same operation but must never create a second user-visible alert for the same key.

## Priority and suppression

- P0: invalidation, stop, material market-regime deterioration.
- P1: enters buy zone, activation, important rank entry/exit.
- P2: thesis/fundamental event.
- P3: watch-state improvement and low-urgency digest material.

Suppress when data is MOCK/STALE/INSUFFICIENT, the state did not materially change, confirmation failed, cooldown is active, consent is missing, or the recommendation has expired/closed. P0 may bypass ordinary digest batching but never consent, tier-entitlement or data-quality gates.

## Highest-tier internal delivery

The internal/admin highest-tier group is:

- `nguyenlinhns@gmail.com`
- `Anh.le2910@gmail.com`
- `phuonghan666@gmail.com`
- `leanhtkv@gmail.com`

All four receive the same highest available Premium report/alert version when delivery is permitted by the production security gate. This group is internal-only metadata and must not appear in public/customer-facing content.

## Signup and preference path

Once production Auth email delivery is ready, the account-based funnel is the authoritative path:

1. Signup collects email/password plus optional, non-prechecked `DAILY_BRIEF` and `EVENT_ALERT` intent.
2. Terms/Privacy acceptance and product-email consent are recorded server-side.
3. Email verification activates the account. A consented Free daily preference may then be enabled; actual sending still depends on the delivery gate.
4. Account settings allow preference changes and consent withdrawal.
5. Watchlist rows can store per-ticker `alert_enabled`; this does not bypass the Premium event-alert entitlement.

The browser never becomes the email sender and never holds provider secrets.

## Mandatory production controls

Before enabling actual delivery: verified sender domain; production-grade Auth SMTP; double opt-in or documented lawful consent basis; one-click unsubscribe; suppression list; bounce/complaint handling; rate limits; encrypted secrets; minimal retention; delivery audit; provider webhook verification; disaster disable switch; and Vietnamese legal/privacy review.

GitHub Pages hosts the pending-interest, signup/account and preference UI, but does not send product email itself. Public account signup remains fail-closed while production Auth email delivery is not proven ready. Product email delivery remains disabled until the backend provider/security gate is deliberately opened with evidence.
