# StockRadar Email Specification V2.1.3

Email is the primary retention channel for registered users and the premium delivery channel for Trial/Paid users.

## Privacy boundary — mandatory

StockRadar must never expose a founder/admin/user's private holdings, private watchlist, personal priority tickers, personal cost basis, position-management levels, or language implying that a public ticker belongs to a specific person.

Internal research may prioritize specific tickers for QA or monitoring, but public/customer-facing output must not label them as “mã ưu tiên của thầy”, “mã đang nắm”, “ba mã ưu tiên”, “danh mục cá nhân”, or equivalent. If an internally prioritized ticker independently qualifies through the same objective HOSE ranking/gating used for everyone, it may appear as a normal market pick with no reference to private ownership or special status.

Customer emails, website pages, public reports, marketing materials, and shared screenshots must contain only market-wide/objective output or that recipient's own explicitly requested data. Personal/private position-management rules are restricted to private internal/admin channels.

## Entitlement boundary

- Unregistered: no content email.
- Registered Free: daily free brief allowed only after email verification and explicit product consent. The Free brief must not reveal premium buy/sell-map detail; it may contain market overview, limited objective shortlist, education/value content and a Premium upgrade CTA.
- Trial/Paid: premium product email only after email verification and explicit product consent.

Public copy may say: “MIỄN PHÍ: nhận bản rà soát thị trường cơ bản. NÂNG CAO: StockRadar chủ động theo dõi và gửi thông tin quan trọng, bao gồm cảnh báo điểm mua/bán theo các mốc quét trong phiên.” Do not claim tick-level realtime.

## Products

- Free daily brief: market state, limited objective highlights/sector highlights and Premium upgrade CTA; no private/user-specific holdings and no premium buy/sell map.
- Personalized Premium daily brief: market state, meaningful changes, followed tickers selected by that recipient, preferred horizons/sectors, new recommendation only when one exists, recommendation changes and current lifecycle state.
- Event alert: activated, invalidated, target/stop/expiry, market-regime or watchlist change.
- Post-session digest: new/closed records and lifecycle summary.
- Weekly transparency report: open/closed/unactivated counts and upcoming watch items.

## Premium feature copy

Premium may include:

- Buy/Sell action alerts at official checkpoints 10:30, 11:15, 13:30 and 14:15 Vietnam time.
- Pocket Pivot, Early Breakout, Confirmed Breakout, Retest/Add-on, Reduce, Stop/Exit.
- Buy Zone, Stop-loss, Target, Upside/Downside and Risk/Reward where supported by evidence.
- Top stocks across HOSE and top stocks by sector.
- Short-term, 3–6 month and 12-month analytical horizons where data supports them.

## Delivery contract

Verified consent, confirmed sender/domain, unsubscribe and preference center, suppression list, bounce/complaint processing, delivery log, signed links, idempotency key, duplicate protection, debounce and cooldown are mandatory.

Official in-session scan checkpoints are 10:30, 11:15, 13:30 and 14:15 Vietnam time. Worker cadence may be higher, but alerts require confirmation and must not claim tick-level realtime.

If no new recommendation passes the gate, the paid email says so and may summarize existing market-wide records, followed tickers selected by that recipient, market state, Top changes and risk alerts. It never creates a recommendation merely to fill an email.

## Internal highest-tier recipients

`nguyenlinhns@gmail.com` and `Anh.le2910@gmail.com` are internal/admin recipients that should receive the highest available Premium version by default. This internal rule must never be surfaced to public/customer-facing output. It does not authorize bypassing provider/compliance/delivery security gates.

## Implemented foundation — 2026-09-03

The Supabase production project contains:

- `public.product_email_preferences`: product-email preferences with RLS.
- `public.product_email_consent_events`: append-only owner-scoped consent history with RLS.
- `private.email_outbox`: provider-neutral idempotent delivery queue, not exposed to browser roles.
- `private.email_suppressions`: unsubscribe/bounce/complaint/security suppression state, not exposed to browser roles.
- `private.email_delivery_gate`: one-row fail-closed production gate.
- `private.product_email_eligibility`: private security-invoker view combining tier, account status, latest consent version, suppression and delivery gate.

The delivery gate cannot set `sending_enabled=true` unless provider configuration, sender-domain verification, unsubscribe, bounce/complaint handling, compliance approval and an evidence reference are all present. Current state remains **sending disabled** until those conditions are met.

## Signup and account preference funnel — 2026-09-03

The production website has one account-based funnel for the two primary email goals:

- signup captures optional, non-prechecked intent for `DAILY_BRIEF` and `EVENT_ALERT`;
- legal acceptance and product-email intent are passed into Supabase Auth user metadata at signup;
- `handle_new_user` stores Terms/Privacy receipts and, when at least one product-email option is selected, creates fail-closed email preferences plus an append-only `SIGNUP` consent event;
- after email verification, a Free account that explicitly selected the daily brief may have that preference enabled automatically; actual provider delivery still remains subject to the delivery gate;
- Free may retain Premium-alert interest in preferences, but the private eligibility view masks Premium-only products unless the account tier is Trial/Paid;
- the account center lets an authenticated user change daily-report and buy/sell-alert preferences and withdraw consent;
- each watchlist row stores `alert_enabled` so later event delivery can respect ticker-level alert preferences;
- production CI verifies the signup fields, account preference center, required assets and no-demo public surface.

This separation is mandatory: **preference/consent is not delivery entitlement**. A selected Premium alert on a Free account must never be interpreted by a sender as authorization to deliver a Premium buy/sell alert.

## Analytics and privacy

Track `email_open` and `email_click` only where lawful and consented. Do not include broker credentials, private portfolio values, private holdings, personal cost basis or individualized order language in public/customer-wide content. Every email states data time, horizon, lifecycle state, and informational/educational boundary.

## Production status

Consent/outbox/suppression/delivery-gate foundation: **PASS**.

Signup/account preference funnel and tier-aware entitlement boundary: **PASS**.

Actual product-email sending remains governed by the fail-closed delivery gate and must not be bypassed.
