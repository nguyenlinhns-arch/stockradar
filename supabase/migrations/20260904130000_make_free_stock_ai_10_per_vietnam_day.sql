-- StockRadar AI becomes the primary Free product surface.
-- Free users receive 10 successful AI requests per Vietnam calendar day.
-- Other API buckets and Trial/Paid limits remain on their existing rolling-window policies.

alter table private.stock_api_rate_limit_policies
  drop constraint if exists stock_api_rate_limit_policies_window_seconds_check;

alter table private.stock_api_rate_limit_policies
  add constraint stock_api_rate_limit_policies_window_seconds_check
  check (window_seconds between 10 and 86400);

insert into private.stock_api_rate_limit_policies(
  account_tier,
  bucket,
  requests_per_window,
  window_seconds,
  active,
  updated_at
)
values ('FREE', 'stock_ai', 10, 86400, true, now())
on conflict (account_tier, bucket) do update
  set requests_per_window = excluded.requests_per_window,
      window_seconds = excluded.window_seconds,
      active = true,
      updated_at = now();

-- Clear only the old Free stock_ai rolling windows so no user inherits the previous hourly window.
delete from private.stock_api_rate_limit_windows w
using public.profiles p
where p.id = w.user_id
  and p.account_tier = 'FREE'
  and w.bucket = 'stock_ai';

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
  v_expected_start timestamptz;
  v_window_end timestamptz;
  v_count integer;
  v_now timestamptz := now();
  v_remaining integer;
  v_retry_after integer := 0;
  v_is_free_stock_ai_daily boolean := false;
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

  v_is_free_stock_ai_daily := v_tier = 'FREE' and p_bucket = 'stock_ai';
  if v_is_free_stock_ai_daily then
    -- Reset exactly at 00:00 Asia/Ho_Chi_Minh, not 24h after a user's first question.
    v_expected_start := (
      date_trunc('day', v_now at time zone 'Asia/Ho_Chi_Minh')
      at time zone 'Asia/Ho_Chi_Minh'
    );
    v_window_end := (
      (date_trunc('day', v_now at time zone 'Asia/Ho_Chi_Minh') + interval '1 day')
      at time zone 'Asia/Ho_Chi_Minh'
    );
  end if;

  perform pg_advisory_xact_lock(hashtextextended(p_user_id::text || ':' || p_bucket, 0));

  select window_started_at, request_count
    into v_window_start, v_count
  from private.stock_api_rate_limit_windows
  where user_id = p_user_id and bucket = p_bucket
  for update;

  if v_is_free_stock_ai_daily then
    if v_window_start is null or v_window_start <> v_expected_start then
      insert into private.stock_api_rate_limit_windows(user_id, bucket, window_started_at, request_count, updated_at)
      values (p_user_id, p_bucket, v_expected_start, 1, v_now)
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
        'daily_reset_timezone', 'Asia/Ho_Chi_Minh',
        'reset_at', v_window_end,
        'retry_after', 0
      );
    end if;
  elsif v_window_start is null or v_window_start + make_interval(secs => v_window_seconds) <= v_now then
    v_window_end := v_now + make_interval(secs => v_window_seconds);
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
      'reset_at', v_window_end,
      'retry_after', 0
    );
  end if;

  if not v_is_free_stock_ai_daily then
    v_window_end := v_window_start + make_interval(secs => v_window_seconds);
  end if;

  if v_count >= v_limit then
    v_retry_after := greatest(
      ceil(extract(epoch from (v_window_end - v_now)))::integer,
      1
    );
    return jsonb_build_object(
      'allowed', false,
      'reason', 'RATE_LIMITED',
      'limit', v_limit,
      'remaining', 0,
      'window_seconds', v_window_seconds,
      'daily_reset_timezone', case when v_is_free_stock_ai_daily then 'Asia/Ho_Chi_Minh' else null end,
      'reset_at', v_window_end,
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
    'daily_reset_timezone', case when v_is_free_stock_ai_daily then 'Asia/Ho_Chi_Minh' else null end,
    'reset_at', v_window_end,
    'retry_after', 0
  );
end;
$$;

revoke all on function public.consume_stockradar_api_quota(uuid, text) from public, anon, authenticated;
grant execute on function public.consume_stockradar_api_quota(uuid, text) to service_role;
