# StockRadar Analytics Specification V2

Canonical event schema: `growth/analytics/event.schema.json`.

## Product events

`top_view`, `horizon_change`, `sector_view`, `recommendation_list_view`, `performance_view`, `stock_search`, `sample_premium_report_view`, `signup_start`, `signup_complete`, `pro_view`, `checkout_start`, `payment_complete`, `email_open`, `email_click`, `renewal_complete`.

## North-star diagnostic chain

Qualified public value view → activated signup → D1/D7 return → email engagement → Advanced intent → verified payment/renewal. Activation requires a meaningful product action, not merely a page impression.

## Dimensions

Horizon, proposition, page, ticker only when public/non-sensitive, recommendation mode, record mode, mock/live, data grade, UTM and experiment cell. Never transmit holdings, portfolio value, broker identity, credentials, OTP or free-text investment conversation.

## Integrity

Signup/payment/renewal are server-confirmed; events use idempotency; bot/internal traffic is segmented; raw data is retained separately from derived funnels; schema versions are immutable; legacy V1 names remain compatibility-only. MOCK/SHADOW traffic cannot be reported as production adoption or revenue.
