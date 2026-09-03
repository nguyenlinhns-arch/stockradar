# Email Architecture Contract

Status: signup/consent and pre-auth interest capture foundations implemented; no production sender is connected.

## Entitlement gate

Transactional mail is available where required for every account tier.

Product-email entitlement is split by product, not by one global Premium-only switch:

- `daily`: Free/Trial/Paid after email verification and explicit product consent. Free receives the basic 09:00 review; Trial/Paid may receive the richer Premium version.
- `state_change` / buy-sell event alerts: Trial/Paid only after verification and explicit product consent.
- `post_session` and `weekly`: Trial/Paid only.

This separation is mandatory. A Free account may store interest in Premium alerts, but the private eligibility layer masks those alert products until the tier becomes Trial/Paid. Preference data is not delivery entitlement.

## Pre-auth email interest path

While production Auth SMTP remains closed, the public website may collect a minimal pending registration request without pretending that signup or delivery is complete.

1. The visitor enters an email and explicitly selects `DAILY_BRIEF`, `EVENT_ALERT`, or both. Nothing is pre-checked.
2. The visitor explicitly accepts the current privacy/consent version.
3. GitHub Pages calls the public `email-interest` Edge Function. The browser receives no service-role/provider secret.
4. The Edge Function enforces allowed origins, JSON/body limits, a honeypot and a daily-hashed technical request fingerprint for rate limiting.
5. Only the Edge Function's service role may invoke `public.capture_email_subscription_interest`; `anon` and `authenticated` have no direct execute grant.
6. The request is stored in `private.email_subscription_intents` as `PENDING_VERIFICATION` for at most 30 days. It is interest only and never authorizes delivery.
7. A later claim flow may enable a Free daily brief only after email control is proven and current consent exists. Premium alerts still require Trial/Paid entitlement.

## Delivery windows

| Window | Purpose | Default content |
| --- | --- | --- |
| 09:00 Vietnam time | Daily pre-session report | Free: basic market review and limited objective highlights. Trial/Paid: richer Premium report according to available data and entitlement. |
| 10:30 / 11:15 / 13:30 / 14:15 | Confirmed state changes | Premium only: P0 risk/invalidation, then P1 readiness/trigger such as buy/sell actions when the signal gate passes. |
| After session | Freeze the close | Premium snapshot summary, new/changed/expired recommendations. |
| Weekly | Review process | Premium state transitions, immutable outcomes and method note. |

These are scheduled scans, not realtime-by-the-second promises. An intraday scan may produce no email when no actionable state change reaches the required gate.

## Daily report contract

Every product email carries separate `report_date`, `market_session_reference`, `data_cutoff_at` and `generated_at` fields. The 09:00 report uses the latest verified data available at generation time. If that data is from the previous trading session, the email must show both dates explicitly.

Canonical daily subject:

`[StockRadar][dd/mm/yyyy] Báo cáo thị trường hàng ngày`

Free daily content must stay basic: market state, limited objective stock/sector highlights and an upgrade path. It must not expose Premium Buy Zone/Stop/Target/Risk-Reward maps or intraday action alerts.

Premium may include deeper analysis, recommendation lifecycle changes and recipient-specific watchlist/horizon ordering where lawful and supported.

## Intraday alert contract

Premium action alerts are evaluated at 10:30, 11:15, 13:30 and 14:15 Vietnam time. Only send when the relevant state change is confirmed and all data/entitlement/consent gates pass. Examples include Pocket Pivot, Early Breakout, Confirmed Breakout, Retest/Add-on, Reduce and Stop/Exit.

Example subjects:

- `[CHỨNG KHOÁN][dd/mm/yyyy] ĐẠT ĐIỂM MUA – <MÃ>`
- `[CHỨNG KHOÁN][dd/mm/yyyy] CẢNH BÁO BÁN – <MÃ>`

## Priority and suppression

- P0: invalidation, stop, material market-regime deterioration.
- P1: enters buy zone, activation, important rank entry/exit.
- P2: thesis/fundamental event.
- P3: watch-state improvement and low-urgency digest material.

Suppress when data is MOCK/STALE/INSUFFICIENT, the state did not materially change, confirmation failed, cooldown is active, consent is missing, the recommendation has expired/closed, or the recipient lacks entitlement for that specific product. Free may pass the daily entitlement but never the Premium buy/sell-alert entitlement.

## Signup and preference path

Once production Auth email delivery is ready, the account-based funnel is the authoritative path:

1. Signup collects email/password plus optional, non-prechecked `DAILY_BRIEF` and `EVENT_ALERT` choices.
2. Terms/Privacy acceptance and product-email consent are recorded server-side.
3. Email verification activates the account. A Free account that selected the daily brief may enable the basic 09:00 product. A selected Premium alert remains preference-only while the tier is Free.
4. Trial/Paid may enable selected Premium alerts after verification, consent and delivery-gate checks.
5. Account settings allow preference changes and consent withdrawal.
6. Watchlist rows can store per-ticker `alert_enabled`; this never bypasses Premium entitlement.

The browser never becomes the email sender and never holds provider secrets.

## Mandatory production controls

Before enabling actual delivery: verified sender domain; production-grade Auth SMTP; documented consent basis; one-click unsubscribe; suppression list; bounce/complaint handling; rate limits; encrypted secrets; minimal retention; delivery audit; provider webhook verification; disaster disable switch; and Vietnamese legal/privacy review.

GitHub Pages hosts the pending-interest, signup/account and preference UI, but does not send product email itself. Public account signup remains fail-closed while production Auth email delivery is not proven ready. Product email delivery remains disabled until the backend provider/security gate is deliberately opened with evidence.
