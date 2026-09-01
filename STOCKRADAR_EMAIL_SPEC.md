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

## Analytics and privacy

Track `email_open` and `email_click` only where lawful and consented. Do not include broker credentials, portfolio values, private holdings or individualized order language. Every email states data time, horizon, lifecycle state, and informational/educational boundary.

Production sending remains BLOCKED until provider, privacy, consent, unsubscribe, security and compliance gates pass.
