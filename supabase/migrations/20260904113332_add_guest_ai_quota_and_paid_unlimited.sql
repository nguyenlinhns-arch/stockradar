-- StockRadar AI access model:
-- Guest: 3 AI questions per Vietnam calendar day.
-- Free: existing 10 AI questions per Vietnam calendar day.
-- Paid: unlimited StockRadar AI requests while the account is ACTIVE.

create table if not exists private.stock_ai_guest_daily_usage (
  guest_key_hash text not null,
  usage_date date not null,
  request_count integer not null default 0 check (request_count >= 0),
  updated_at timestamptz not null default now(),
  primary key (guest_key_hash, usage_date),
  constraint stock_ai_guest_daily_usage_hash_check check (guest_key_hash ~ '^[a-f0-9]{64}$')
);

alter table private.stock_ai_guest_daily_usage enable row level security;
revoke all on table private.stock_ai_guest_daily_usage from public, anon, authenticated;
grant select, insert, update, delete on table private.stock_ai_guest_daily_usage to service_role;

create or replace function public.consume_stockradar_guest_ai_quota(p_guest_key_hash text)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_hash text := lower(trim(coalesce(p_guest_key_hash, '')));
  v_usage_date date := (now() at time zone 'Asia/Ho_Chi_Minh')::date;
  v_reset_at timestamptz := (((now() at time zone 'Asia/Ho_Chi_Minh')::date + 1)::timestamp at time zone 'Asia/Ho_Chi_Minh');
  v_count integer := 0;
  v_limit integer := 3;
  v_retry_after integer := 0;
begin
  if v_hash !~ '^[a-f0-9]{64}$' then
    return jsonb_build_object('allowed', false, 'reason', 'INVALID_GUEST_KEY');
  end if;

  perform pg_advisory_xact_lock(hashtextextended('stock_ai_guest:' || v_hash || ':' || v_usage_date::text, 0));

  select u.request_count
    into v_count
  from private.stock_ai_guest_daily_usage u
  where u.guest_key_hash = v_hash
    and u.usage_date = v_usage_date
  for update;

  v_count := coalesce(v_count, 0);
  if v_count >= v_limit then
    v_retry_after := greatest(ceil(extract(epoch from (v_reset_at - now())))::integer, 1);
    return jsonb_build_object(
      'allowed', false,
      'reason', 'RATE_LIMITED',
      'limit', v_limit,
      'remaining', 0,
      'reset_at', v_reset_at,
      'daily_reset_timezone', 'Asia/Ho_Chi_Minh',
      'retry_after', v_retry_after
    );
  end if;

  insert into private.stock_ai_guest_daily_usage(guest_key_hash, usage_date, request_count, updated_at)
  values (v_hash, v_usage_date, 1, now())
  on conflict (guest_key_hash, usage_date) do update
    set request_count = private.stock_ai_guest_daily_usage.request_count + 1,
        updated_at = now()
  returning request_count into v_count;

  return jsonb_build_object(
    'allowed', true,
    'limit', v_limit,
    'remaining', greatest(v_limit - v_count, 0),
    'reset_at', v_reset_at,
    'daily_reset_timezone', 'Asia/Ho_Chi_Minh',
    'retry_after', 0
  );
end;
$$;

revoke all on function public.consume_stockradar_guest_ai_quota(text) from public, anon, authenticated;
grant execute on function public.consume_stockradar_guest_ai_quota(text) to service_role;

alter function public.consume_stockradar_api_quota(uuid, text) rename to consume_stockradar_api_quota_limited_v1;
revoke all on function public.consume_stockradar_api_quota_limited_v1(uuid, text) from public, anon, authenticated;
grant execute on function public.consume_stockradar_api_quota_limited_v1(uuid, text) to service_role;

create function public.consume_stockradar_api_quota(p_user_id uuid, p_bucket text)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_tier text;
  v_status text;
begin
  select p.account_tier, p.account_status
    into v_tier, v_status
  from public.profiles p
  where p.id = p_user_id;

  if v_status = 'ACTIVE' and v_tier = 'PAID' and trim(coalesce(p_bucket, '')) = 'stock_ai' then
    return jsonb_build_object(
      'allowed', true,
      'unlimited', true,
      'limit', null,
      'remaining', null,
      'window_seconds', null,
      'reset_at', null,
      'retry_after', 0
    );
  end if;

  return public.consume_stockradar_api_quota_limited_v1(p_user_id, p_bucket);
end;
$$;

revoke all on function public.consume_stockradar_api_quota(uuid, text) from public, anon, authenticated;
grant execute on function public.consume_stockradar_api_quota(uuid, text) to service_role;
