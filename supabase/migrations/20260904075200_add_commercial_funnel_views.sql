create view private.conversion_funnel_30d_v1
with (security_invoker = true)
as
with base as (
  select event_name, session_hash
  from private.conversion_funnel_events
  where occurred_at >= now() - interval '30 days'
), counts as (
  select
    count(distinct session_hash) filter (where event_name = 'home_view') as home_sessions,
    count(distinct session_hash) filter (where event_name = 'ticker_lookup_submit') as lookup_sessions,
    count(distinct session_hash) filter (where event_name = 'premium_preview_view') as premium_preview_sessions,
    count(distinct session_hash) filter (where event_name = 'premium_sample_view') as premium_sample_sessions,
    count(distinct session_hash) filter (where event_name = 'pricing_view') as pricing_sessions,
    count(distinct session_hash) filter (where event_name = 'signup_premium_view') as premium_signup_sessions,
    count(distinct session_hash) filter (where event_name = 'signup_submit') as signup_submit_sessions,
    count(distinct session_hash) filter (where event_name = 'checkout_view') as checkout_sessions
  from base
)
select
  home_sessions,
  lookup_sessions,
  premium_preview_sessions,
  premium_sample_sessions,
  pricing_sessions,
  premium_signup_sessions,
  signup_submit_sessions,
  checkout_sessions,
  round(100.0 * lookup_sessions / nullif(home_sessions, 0), 2) as home_to_lookup_pct,
  round(100.0 * premium_preview_sessions / nullif(lookup_sessions, 0), 2) as lookup_to_preview_pct,
  round(100.0 * pricing_sessions / nullif(premium_preview_sessions, 0), 2) as preview_to_pricing_pct,
  round(100.0 * premium_signup_sessions / nullif(pricing_sessions, 0), 2) as pricing_to_premium_signup_pct,
  round(100.0 * checkout_sessions / nullif(premium_signup_sessions, 0), 2) as premium_signup_to_checkout_pct
from counts;

revoke all on private.conversion_funnel_30d_v1 from public, anon, authenticated;

create view private.conversion_ticker_interest_30d_v1
with (security_invoker = true)
as
select
  ticker,
  count(*) filter (where event_name = 'ticker_lookup_submit') as lookup_events,
  count(distinct session_hash) filter (where event_name = 'ticker_lookup_submit') as lookup_sessions,
  count(*) filter (where event_name in ('premium_preview_view', 'conversion_click')) as premium_interest_events,
  count(distinct session_hash) filter (where event_name in ('premium_preview_view', 'conversion_click')) as premium_interest_sessions,
  max(occurred_at) as last_interest_at
from private.conversion_funnel_events
where occurred_at >= now() - interval '30 days'
  and ticker is not null
group by ticker
order by premium_interest_sessions desc, lookup_sessions desc, ticker;

revoke all on private.conversion_ticker_interest_30d_v1 from public, anon, authenticated;
