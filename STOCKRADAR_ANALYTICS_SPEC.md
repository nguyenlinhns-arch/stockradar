# StockRadar Analytics Specification V2.1.2

Canonical event schema: `growth/analytics/event.schema.json`.

## Product events

Core: `top_view`, `horizon_change`, `sector_view`, `recommendation_public_view`, `recommendation_history_view`, `performance_view`, `today_changes_view`, `benchmark_view`, `four_horizon_view`, `holding_view`, `signup_start`, `signup_complete`, `pro_view`, `checkout_start`, `payment_complete`, `email_open`, `email_click`, `renewal_complete`.

Ticker funnel: `ticker_input_started`, `ticker_autocomplete_selected`, `ticker_search_submitted`, `ticker_search_valid`, `ticker_search_invalid`, `ticker_cache_hit`, `ticker_cache_miss`, `quick_report_view`, `full_report_requested`, `report_generation_completed`, `report_generation_failed`, `ticker_trial_cta_clicked`, `ticker_watch_started`.

Onboarding/email: `onboarding_horizon_selected`, `onboarding_sector_selected`, `onboarding_ticker_added`, `paid_email_preference_changed`.

## North-star diagnostic chain

Ads → public data view → ticker search → four-horizon/holding/history view → Free/Trial signup → onboarding → D1/D7 return → Paid view → checkout → verified payment → email engagement → renewal. Activation requires a meaningful product action, not merely a page impression.

Aggregate ticker popularity stores search count, unique searchers, public views, watchlist count, Trial/Paid conversions and calculation time. It may guide cache pre-warming and Ads, but never replace the full-universe set used for Top ranking.

## Dimensions

Horizon, proposition, page, ticker only when public/non-sensitive, recommendation mode, record mode, mock/live, data grade, UTM and experiment cell. Never transmit holdings, portfolio value, broker identity, credentials, OTP or free-text investment conversation.

## Integrity

Signup/payment/renewal are server-confirmed; events use idempotency; bot/internal traffic is segmented; raw data is retained separately from derived funnels; schema versions are immutable; legacy V1 names remain compatibility-only. MOCK/SHADOW traffic cannot be reported as production adoption or revenue.
