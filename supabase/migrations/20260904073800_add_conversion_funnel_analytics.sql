create table private.conversion_funnel_events (
  id uuid primary key default gen_random_uuid(),
  event_name text not null check (event_name in (
    'home_view',
    'ticker_lookup_submit',
    'stock_report_view',
    'premium_preview_view',
    'premium_sample_view',
    'pricing_view',
    'performance_proof_view',
    'signup_view',
    'signup_premium_view',
    'signup_submit',
    'checkout_view',
    'conversion_click'
  )),
  action_name text check (
    action_name is null or (
      char_length(action_name) between 1 and 80
      and action_name ~ '^[a-z0-9_:-]+$'
    )
  ),
  source_path text not null check (
    char_length(source_path) between 1 and 256
    and left(source_path, 1) = '/'
    and position('?' in source_path) = 0
    and position('#' in source_path) = 0
  ),
  ticker text check (ticker is null or ticker ~ '^[A-Z0-9]{3}$'),
  plan_interest text check (plan_interest is null or plan_interest in ('FREE', 'PREMIUM')),
  session_hash text not null check (session_hash ~ '^[0-9a-f]{64}$'),
  ip_hash text not null check (ip_hash ~ '^[0-9a-f]{64}$'),
  utm_source text check (utm_source is null or char_length(utm_source) <= 120),
  utm_campaign text check (utm_campaign is null or char_length(utm_campaign) <= 160),
  referrer_host text check (referrer_host is null or char_length(referrer_host) <= 253),
  occurred_at timestamptz not null default now()
);

create index conversion_funnel_events_time
  on private.conversion_funnel_events(occurred_at desc);
create index conversion_funnel_events_event_time
  on private.conversion_funnel_events(event_name, occurred_at desc);
create index conversion_funnel_events_session_time
  on private.conversion_funnel_events(session_hash, occurred_at desc);

alter table private.conversion_funnel_events enable row level security;
revoke all on table private.conversion_funnel_events from public, anon, authenticated;

create or replace function public.capture_conversion_event_v1(
  p_event_name text,
  p_action_name text,
  p_source_path text,
  p_ticker text,
  p_plan_interest text,
  p_session_hash text,
  p_ip_hash text,
  p_utm_source text,
  p_utm_campaign text,
  p_referrer_host text
)
returns void
language plpgsql
security definer
set search_path = pg_catalog, public, private
as $$
declare
  v_recent_ip_count integer;
  v_event_name text := lower(trim(coalesce(p_event_name, '')));
  v_action_name text := nullif(lower(trim(coalesce(p_action_name, ''))), '');
  v_source_path text := trim(coalesce(p_source_path, ''));
  v_ticker text := nullif(upper(trim(coalesce(p_ticker, ''))), '');
  v_plan text := nullif(upper(trim(coalesce(p_plan_interest, ''))), '');
begin
  if v_event_name not in (
    'home_view', 'ticker_lookup_submit', 'stock_report_view', 'premium_preview_view',
    'premium_sample_view', 'pricing_view', 'performance_proof_view', 'signup_view',
    'signup_premium_view', 'signup_submit', 'checkout_view', 'conversion_click'
  ) then
    raise exception 'invalid conversion event';
  end if;

  if char_length(v_source_path) < 1 or char_length(v_source_path) > 256
     or left(v_source_path, 1) <> '/'
     or position('?' in v_source_path) > 0
     or position('#' in v_source_path) > 0 then
    raise exception 'invalid source path';
  end if;

  if v_action_name is not null and (
    char_length(v_action_name) > 80 or v_action_name !~ '^[a-z0-9_:-]+$'
  ) then
    raise exception 'invalid action name';
  end if;

  if v_ticker is not null and v_ticker !~ '^[A-Z0-9]{3}$' then
    raise exception 'invalid ticker';
  end if;

  if v_plan is not null and v_plan not in ('FREE', 'PREMIUM') then
    raise exception 'invalid plan';
  end if;

  if coalesce(p_session_hash, '') !~ '^[0-9a-f]{64}$'
     or coalesce(p_ip_hash, '') !~ '^[0-9a-f]{64}$' then
    raise exception 'invalid anonymous fingerprint';
  end if;

  select count(*)::integer
  into v_recent_ip_count
  from private.conversion_funnel_events
  where ip_hash = p_ip_hash
    and occurred_at >= now() - interval '1 minute';

  if v_recent_ip_count >= 60 then
    raise exception 'rate limit exceeded';
  end if;

  insert into private.conversion_funnel_events (
    event_name,
    action_name,
    source_path,
    ticker,
    plan_interest,
    session_hash,
    ip_hash,
    utm_source,
    utm_campaign,
    referrer_host
  ) values (
    v_event_name,
    v_action_name,
    v_source_path,
    v_ticker,
    v_plan,
    p_session_hash,
    p_ip_hash,
    nullif(left(trim(coalesce(p_utm_source, '')), 120), ''),
    nullif(left(trim(coalesce(p_utm_campaign, '')), 160), ''),
    nullif(left(lower(trim(coalesce(p_referrer_host, ''))), 253), '')
  );
end;
$$;

revoke all on function public.capture_conversion_event_v1(
  text, text, text, text, text, text, text, text, text, text
) from public, anon, authenticated;
grant execute on function public.capture_conversion_event_v1(
  text, text, text, text, text, text, text, text, text, text
) to service_role;

create view private.conversion_funnel_daily
with (security_invoker = true)
as
select
  date_trunc('day', occurred_at) as day,
  event_name,
  coalesce(plan_interest, 'UNSPECIFIED') as plan_interest,
  count(*) as events,
  count(distinct session_hash) as sessions
from private.conversion_funnel_events
group by 1, 2, 3;

revoke all on private.conversion_funnel_daily from public, anon, authenticated;
