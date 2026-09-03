create table private.stock_api_gate (
  singleton boolean primary key default true check (singleton),
  data_ready boolean not null default false,
  data_rights_approved boolean not null default false,
  compliance_approved boolean not null default false,
  api_enabled boolean not null default false,
  evidence_ref text,
  updated_at timestamptz not null default now(),
  constraint stock_api_gate_safe_enable check (
    not api_enabled or (
      data_ready
      and data_rights_approved
      and compliance_approved
      and length(trim(coalesce(evidence_ref, ''))) > 0
    )
  )
);

insert into private.stock_api_gate (singleton)
values (true)
on conflict (singleton) do nothing;

create table private.stock_report_cache (
  ticker text not null check (ticker ~ '^[A-Z]{3}$'),
  horizon text not null check (horizon in ('SHORT_TERM','MEDIUM_TERM','LONG_TERM','ACCUMULATION')),
  snapshot_id text not null,
  generated_at timestamptz not null,
  expires_at timestamptz not null,
  payload jsonb not null,
  source_manifest_ref text not null,
  primary key (ticker, horizon),
  constraint stock_report_cache_window check (expires_at > generated_at)
);

create table private.stock_api_rate_limit_policies (
  account_tier text not null check (account_tier in ('FREE','TRIAL','PAID')),
  bucket text not null,
  requests_per_window integer not null check (requests_per_window > 0),
  window_seconds integer not null check (window_seconds between 10 and 3600),
  active boolean not null default true,
  updated_at timestamptz not null default now(),
  primary key (account_tier, bucket)
);

insert into private.stock_api_rate_limit_policies(account_tier, bucket, requests_per_window, window_seconds)
values
  ('FREE', 'stock_report', 30, 60),
  ('TRIAL', 'stock_report', 90, 60),
  ('PAID', 'stock_report', 180, 60)
on conflict (account_tier, bucket) do nothing;

create table private.stock_api_rate_limit_windows (
  user_id uuid not null references auth.users(id) on delete cascade,
  bucket text not null,
  window_started_at timestamptz not null,
  request_count integer not null default 0 check (request_count >= 0),
  updated_at timestamptz not null default now(),
  primary key (user_id, bucket)
);

create or replace function public.consume_stockradar_api_quota(
  p_user_id uuid,
  p_bucket text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_tier text;
  v_status text;
  v_limit integer;
  v_window_seconds integer;
  v_window_start timestamptz;
  v_count integer;
  v_now timestamptz := now();
  v_remaining integer;
  v_retry_after integer := 0;
begin
  if p_user_id is null or length(trim(coalesce(p_bucket, ''))) = 0 then
    return jsonb_build_object('allowed', false, 'reason', 'INVALID_REQUEST');
  end if;

  select p.account_tier, p.account_status
    into v_tier, v_status
  from public.profiles p
  where p.id = p_user_id;

  if v_status <> 'ACTIVE' or v_tier is null then
    return jsonb_build_object('allowed', false, 'reason', 'ACCOUNT_INACTIVE');
  end if;

  select policy.requests_per_window, policy.window_seconds
    into v_limit, v_window_seconds
  from private.stock_api_rate_limit_policies policy
  where policy.account_tier = v_tier
    and policy.bucket = p_bucket
    and policy.active is true;

  if v_limit is null or v_window_seconds is null then
    return jsonb_build_object('allowed', false, 'reason', 'POLICY_MISSING');
  end if;

  perform pg_advisory_xact_lock(hashtextextended(p_user_id::text || ':' || p_bucket, 0));

  select window_started_at, request_count
    into v_window_start, v_count
  from private.stock_api_rate_limit_windows
  where user_id = p_user_id and bucket = p_bucket
  for update;

  if v_window_start is null or v_window_start + make_interval(secs => v_window_seconds) <= v_now then
    insert into private.stock_api_rate_limit_windows(user_id, bucket, window_started_at, request_count, updated_at)
    values (p_user_id, p_bucket, v_now, 1, v_now)
    on conflict (user_id, bucket) do update
      set window_started_at = excluded.window_started_at,
          request_count = 1,
          updated_at = excluded.updated_at;
    v_count := 1;
    v_remaining := greatest(v_limit - v_count, 0);
    return jsonb_build_object(
      'allowed', true,
      'limit', v_limit,
      'remaining', v_remaining,
      'window_seconds', v_window_seconds,
      'retry_after', 0
    );
  end if;

  if v_count >= v_limit then
    v_retry_after := greatest(
      ceil(extract(epoch from ((v_window_start + make_interval(secs => v_window_seconds)) - v_now)))::integer,
      1
    );
    return jsonb_build_object(
      'allowed', false,
      'reason', 'RATE_LIMITED',
      'limit', v_limit,
      'remaining', 0,
      'window_seconds', v_window_seconds,
      'retry_after', v_retry_after
    );
  end if;

  update private.stock_api_rate_limit_windows
     set request_count = request_count + 1,
         updated_at = v_now
   where user_id = p_user_id and bucket = p_bucket
   returning request_count into v_count;

  v_remaining := greatest(v_limit - v_count, 0);
  return jsonb_build_object(
    'allowed', true,
    'limit', v_limit,
    'remaining', v_remaining,
    'window_seconds', v_window_seconds,
    'retry_after', 0
  );
end;
$$;

create or replace function public.fetch_stockradar_cached_report(
  p_ticker text,
  p_horizon text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_ticker text := upper(trim(coalesce(p_ticker, '')));
  v_horizon text := upper(trim(coalesce(p_horizon, '')));
  v_gate private.stock_api_gate%rowtype;
  v_report private.stock_report_cache%rowtype;
begin
  if v_ticker !~ '^[A-Z]{3}$' then
    return jsonb_build_object('status', 'INVALID_REQUEST', 'reason', 'INVALID_TICKER');
  end if;
  if v_horizon not in ('SHORT_TERM','MEDIUM_TERM','LONG_TERM','ACCUMULATION') then
    return jsonb_build_object('status', 'INVALID_REQUEST', 'reason', 'INVALID_HORIZON');
  end if;

  select * into v_gate from private.stock_api_gate where singleton is true;
  if v_gate.api_enabled is not true then
    return jsonb_build_object('status', 'BLOCKED_DATA_GATE', 'reason', 'PRODUCTION_API_DISABLED');
  end if;

  select * into v_report
  from private.stock_report_cache
  where ticker = v_ticker and horizon = v_horizon;

  if v_report.ticker is null then
    return jsonb_build_object('status', 'NOT_FOUND', 'ticker', v_ticker, 'horizon', v_horizon);
  end if;
  if v_report.expires_at <= now() then
    return jsonb_build_object('status', 'BLOCKED_DATA_GATE', 'reason', 'REPORT_STALE', 'ticker', v_ticker, 'horizon', v_horizon);
  end if;

  return jsonb_build_object(
    'status', 'READY',
    'ticker', v_report.ticker,
    'horizon', v_report.horizon,
    'snapshot_id', v_report.snapshot_id,
    'generated_at', v_report.generated_at,
    'expires_at', v_report.expires_at,
    'payload', v_report.payload
  );
end;
$$;

revoke all on function public.consume_stockradar_api_quota(uuid, text) from public, anon, authenticated;
revoke all on function public.fetch_stockradar_cached_report(text, text) from public, anon, authenticated;
grant execute on function public.consume_stockradar_api_quota(uuid, text) to service_role;
grant execute on function public.fetch_stockradar_cached_report(text, text) to service_role;

alter table private.stock_api_gate enable row level security;
alter table private.stock_report_cache enable row level security;
alter table private.stock_api_rate_limit_policies enable row level security;
alter table private.stock_api_rate_limit_windows enable row level security;

revoke all on table private.stock_api_gate from public, anon, authenticated;
revoke all on table private.stock_report_cache from public, anon, authenticated;
revoke all on table private.stock_api_rate_limit_policies from public, anon, authenticated;
revoke all on table private.stock_api_rate_limit_windows from public, anon, authenticated;
