# StockRadar Email Specification V2.1.2

Email is the primary retention channel for verified Trial and Paid users only.

## Entitlement boundary

- Unregistered: no content email.
- Free: transactional email only (verification, password reset, account/security, payment/renewal where relevant). No daily opportunity, Top 10, market brief, ticker-change alert, closing digest or full weekly report.
- Trial/Paid: product email only after email verification and explicit product consent.

Public copy must say: “MIỄN PHÍ: bạn chủ động vào StockRadar để xem. NÂNG CAO: StockRadar chủ động theo dõi và gửi thông tin quan trọng đến email của bạn.”

## Products

- Personalized daily brief: market state, meaningful changes, followed tickers, preferred horizons/sectors, new recommendation only when one exists, recommendation changes and current P/L.
- Event alert: activated, invalidated, target/stop/expiry, market-regime or watchlist change.
- Post-session digest: new/closed records and lifecycle summary.
- Weekly transparency report: open/closed/unactivated counts and upcoming watch items.

## Delivery contract

Verified consent, confirmed sender/domain, unsubscribe and preference center, suppression list, bounce/complaint processing, delivery log, signed links, idempotency key, duplicate protection, debounce and cooldown are mandatory.

Official in-session scan checkpoints are 10:30, 11:15, 13:30 and 14:15 Vietnam time. Worker cadence may be higher, but alerts require confirmation and must not claim tick-level realtime.

If no new recommendation passes the gate, the paid email says so and may summarize existing records, followed tickers, market state, Top changes and risk alerts. It never creates a recommendation merely to fill an email.

## Implemented foundation — 2026-09-03

The Supabase production project now contains:

- `public.product_email_preferences`: owner-scoped Trial/Paid product-email preferences with RLS.
- `public.product_email_consent_events`: append-only owner-scoped consent history with RLS.
- `private.email_outbox`: provider-neutral idempotent delivery queue, not exposed to browser roles.
- `private.email_suppressions`: unsubscribe/bounce/complaint/security suppression state, not exposed to browser roles.
- `private.email_delivery_gate`: one-row fail-closed production gate.
- `private.product_email_eligibility`: private security-invoker view combining tier, account status, latest consent version, suppression and delivery gate.

The delivery gate cannot set `sending_enabled=true` unless provider configuration, sender-domain verification, unsubscribe, bounce/complaint handling, compliance approval and an evidence reference are all present. Current state remains **sending disabled**.

Free users cannot enable product email at the database entitlement layer. A downgrade to Free or a non-active account automatically disables product email preferences.

## Signup and account preference funnel — 2026-09-03

The production website now has a single account-based funnel for the two primary email goals:

- signup captures optional, non-prechecked intent for `DAILY_BRIEF` and `EVENT_ALERT`;
- legal acceptance and product-email intent are passed into Supabase Auth user metadata at signup;
- the `handle_new_user` trigger stores Terms/Privacy receipts and, when selected, creates fail-closed email preferences plus an append-only `SIGNUP` consent event;
- the account center lets authenticated users change daily-report and buy/sell-alert preferences, with a separate master send switch;
- Free users may save interest/preferences but cannot set `product_email_preferences.enabled=true`;
- Trial/Paid users can enable product email only when the profile is active;
- each watchlist row can store `alert_enabled` so event delivery can later respect ticker-level alert preferences;
- signup links remain fail-closed while production Auth email verification is not ready.

The homepage includes a dedicated conversion surface for “Báo cáo mỗi ngày + cảnh báo mua/bán”. Production CI verifies that the signup fields, account preference center and required email assets are present in the generated Pages artifact.

## Analytics and privacy

Track `email_open` and `email_click` only where lawful and consented. Do not include broker credentials, portfolio values, private holdings or individualized order language. Every email states data time, horizon, lifecycle state, and informational/educational boundary.

## Production status

Consent/outbox/suppression/delivery-gate foundation: **PASS**.

Signup/account preference funnel: **PASS**.

Actual product-email sending: **BLOCKED** until a provider is selected, the StockRadar sending domain is verified, unsubscribe links and preference-center withdrawal are live, bounce/complaint webhooks are processed, provider secrets are stored server-side, compliance approves the content, and the delivery gate is deliberately opened with evidence.
