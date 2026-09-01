# StockRadar Email Specification V2

Email is the primary retention channel.

## Products

- Daily pre-session brief: market state, horizon tops, sectors, new/changed risks.
- Event alert: activated, invalidated, target/stop/expiry, market-regime or watchlist change.
- Post-session digest: new/closed records and lifecycle summary.
- Weekly transparency report: open/closed/unactivated counts and upcoming watch items.

## Delivery contract

Verified consent, confirmed sender/domain, unsubscribe and preference center, suppression list, bounce/complaint processing, delivery log, signed links, idempotency key, duplicate protection, debounce and cooldown are mandatory.

Official in-session scan checkpoints are 10:30, 11:15, 13:30 and 14:15 Vietnam time. Worker cadence may be higher, but alerts require confirmation and must not claim tick-level realtime.

## Analytics and privacy

Track `email_open` and `email_click` only where lawful and consented. Do not include broker credentials, portfolio values, private holdings or individualized order language. Every email states data time, horizon, lifecycle state, and informational/educational boundary.

Production sending remains BLOCKED until provider, privacy, consent, unsubscribe, security and compliance gates pass.
