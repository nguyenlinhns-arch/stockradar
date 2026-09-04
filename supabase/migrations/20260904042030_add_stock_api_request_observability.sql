create table private.stock_api_request_events (
  id bigint generated always as identity primary key,
  occurred_at timestamptz not null default now(),
  user_id uuid references auth.users(id) on delete set null,
  account_tier text check (account_tier is null or account_tier in ('FREE','TRIAL','PAID')),
  ticker text check (ticker is null or ticker ~ '^[A-Z]{3}$'),
  horizon text check (horizon is null or horizon in ('SHORT_TERM','MEDIUM_TERM','LONG_TERM','ACCUMULATION')),
  outcome text not null check (char_length(outcome) between 1 and 64),
  reason text check (reason is null or char_length(reason) <= 96),
  http_status smallint not null check (http_status between 100 and 599),
  latency_ms integer not null check (latency_ms between 0 and 120000),
  rate_limit_remaining integer check (rate_limit_remaining is null or rate_limit_remaining >= 0)
);

create index stock_api_request_events_occurred_idx
  on private.stock_api_request_events (occurred_at desc);
create index stock_api_request_events_user_occurred_idx
  on private.stock_api_request_events (user_id, occurred_at desc)
  where user_id is not null;
create index stock_api_request_events_outcome_occurred_idx
  on private.stock_api_request_events (outcome, occurred_at desc);

alter table private.stock_api_request_events enable row level security;
revoke all on table private.stock_api_request_events from public, anon, authenticated, service_role;

create or replace function public.record_stockradar_api_request_event(
  p_user_id uuid,
  p_ticker text,
  p_horizon text,
  p_outcome text,
  p_reason text,
  p_http_status integer,
  p_latency_ms integer,
  p_rate_limit_remaining integer default null
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_ticker text := upper(trim(coalesce(p_ticker, '')));
  v_horizon text := upper(trim(coalesce(p_horizon, '')));
  v_outcome text := upper(trim(coalesce(p_outcome, '')));
  v_reason text := upper(trim(coalesce(p_reason, '')));
  v_tier text;
begin
  if p_user_id is null then
    return;
  end if;

  select profile.account_tier into v_tier
  from public.profiles profile
  where profile.id = p_user_id;

  if v_ticker !~ '^[A-Z]{3}$' then v_ticker := null; end if;
  if v_horizon not in ('SHORT_TERM','MEDIUM_TERM','LONG_TERM','ACCUMULATION') then v_horizon := null; end if;
  if v_outcome = '' then v_outcome := 'UNKNOWN'; end if;
  v_outcome := left(regexp_replace(v_outcome, '[^A-Z0-9_:-]', '_', 'g'), 64);
  if v_reason = '' then
    v_reason := null;
  else
    v_reason := left(regexp_replace(v_reason, '[^A-Z0-9_:-]', '_', 'g'), 96);
  end if;

  insert into private.stock_api_request_events(
    user_id, account_tier, ticker, horizon, outcome, reason,
    http_status, latency_ms, rate_limit_remaining
  ) values (
    p_user_id,
    case when v_tier in ('FREE','TRIAL','PAID') then v_tier else null end,
    v_ticker,
    v_horizon,
    v_outcome,
    v_reason,
    least(greatest(coalesce(p_http_status, 500), 100), 599),
    least(greatest(coalesce(p_latency_ms, 0), 0), 120000),
    case when p_rate_limit_remaining is null then null else greatest(p_rate_limit_remaining, 0) end
  );
end;
$$;

revoke all on function public.record_stockradar_api_request_event(uuid,text,text,text,text,integer,integer,integer) from public, anon, authenticated;
grant execute on function public.record_stockradar_api_request_event(uuid,text,text,text,text,integer,integer,integer) to service_role;
