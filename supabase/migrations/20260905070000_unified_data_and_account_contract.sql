-- Derived data only. Private sources and raw history remain outside the browser.
create table if not exists private.stock_data_snapshots (
  ticker text primary key check (ticker ~ '^[A-Z0-9]{3}$' and ticker ~ '[A-Z]'),
  as_of_date date not null,
  source_updated_at timestamptz not null,
  snapshot_id text not null,
  data_quality text not null check (data_quality in ('updated','stale','error')),
  payload jsonb not null check (jsonb_typeof(payload)='object'),
  imported_at timestamptz not null default now()
);
alter table private.stock_data_snapshots enable row level security;
revoke all on private.stock_data_snapshots from public,anon,authenticated;
grant all on private.stock_data_snapshots to service_role;

create or replace function public.import_stockradar_data_layer(p_bundle jsonb)
returns jsonb language plpgsql security definer set search_path=''
as $$
declare r jsonb; v_count integer:=0; v_changed integer;
begin
  if coalesce(p_bundle->>'schema_version','') <> 'stockradar.data.v1'
     or coalesce(jsonb_typeof(p_bundle->'records'),'') <> 'array'
     or jsonb_array_length(p_bundle->'records') not between 1 and 500 then
    raise exception 'invalid data bundle';
  end if;
  if exists(select 1 from jsonb_array_elements(p_bundle->'records') x
    group by x->>'symbol' having count(*) > 1) then raise exception 'duplicate ticker'; end if;
  for r in select value from jsonb_array_elements(p_bundle->'records') loop
    if coalesce(r->>'exchange','') <> 'HOSE' or not exists (
      select 1 from private.stock_research_reference_cache where ticker=r->>'symbol'
    ) then raise exception 'unknown HOSE ticker'; end if;
    if (r->>'as_of_date')::date > (now() at time zone 'Asia/Ho_Chi_Minh')::date
       or (r->>'updated_at')::timestamptz > now()+interval '5 minutes'
       or coalesce((r->>'public_action_allowed')::boolean,true) then
      raise exception 'invalid data timestamp or action flag';
    end if;
    insert into private.stock_data_snapshots(ticker,as_of_date,source_updated_at,snapshot_id,data_quality,payload)
    values(r->>'symbol',(r->>'as_of_date')::date,(r->>'updated_at')::timestamptz,p_bundle->>'snapshot_id',r->>'data_quality',r)
    on conflict(ticker) do update set as_of_date=excluded.as_of_date,source_updated_at=excluded.source_updated_at,
      snapshot_id=excluded.snapshot_id,data_quality=excluded.data_quality,payload=excluded.payload,imported_at=now()
    where (excluded.as_of_date,excluded.source_updated_at) >= (stock_data_snapshots.as_of_date,stock_data_snapshots.source_updated_at)
      and excluded.data_quality <> 'error';
    get diagnostics v_changed=row_count;
    v_count:=v_count+v_changed;
  end loop;
  return jsonb_build_object('status','IMPORTED','rows',v_count,'snapshot_id',p_bundle->>'snapshot_id');
end $$;
revoke all on function public.import_stockradar_data_layer(jsonb) from public,anon,authenticated;
grant execute on function public.import_stockradar_data_layer(jsonb) to service_role;

-- Select the newest research/reference observation, never an older ready row.
create or replace function public.fetch_stockradar_ai_context(p_ticker text)
returns jsonb language plpgsql security definer set search_path=''
as $$
declare r record; d private.stock_data_snapshots%rowtype; v_payload jsonb; v_stale boolean;
begin
  select * into r from (
    select ticker,snapshot_id,generated_at,as_of_date,price_snapshot_status,payload,source_ref,true as ready
    from private.stock_research_cache where ticker=upper(trim(p_ticker))
    union all
    select ticker,snapshot_id,generated_at,as_of_date,price_snapshot_status,payload,source_ref,research_ready
    from private.stock_research_reference_cache where ticker=upper(trim(p_ticker))
  ) q order by as_of_date desc, generated_at desc, ready desc limit 1;
  if r.ticker is null then return jsonb_build_object('status','NOT_FOUND','ticker',upper(trim(p_ticker))); end if;
  v_stale:=r.generated_at>now()+interval '5 minutes' or r.generated_at<now()-interval '96 hours'
    or r.as_of_date>(now() at time zone 'Asia/Ho_Chi_Minh')::date
    or r.as_of_date<(now() at time zone 'Asia/Ho_Chi_Minh')::date-4
    or upper(r.price_snapshot_status) ~ 'STALE|INVALID|FAILED';
  v_payload:=r.payload;
  select * into d from private.stock_data_snapshots where ticker=r.ticker;
  if d.ticker is not null and d.as_of_date=r.as_of_date and d.data_quality='updated'
    and abs((d.payload->>'price')::numeric-(r.payload#>>'{quote,price}')::numeric)<0.01 then
    v_payload:=v_payload || jsonb_build_object(
      'technical_detail',d.payload->'technical_detail','fundamental_detail',d.payload->'fundamental_detail',
      'valuation_detail',d.payload->'valuation_detail','history',d.payload->'history',
      'data_quality',d.data_quality,'volume_mode','EOD','data_snapshot_id',d.snapshot_id,
      'quote',coalesce(r.payload->'quote','{}'::jsonb)||coalesce(d.payload->'quote','{}'::jsonb)
    );
  end if;
  return jsonb_build_object('status',case when r.ready then 'INTERNAL_RESEARCH_READY' else 'INTERNAL_REFERENCE_READY' end,
    'context_grade',case when r.ready and not v_stale and coalesce(d.data_quality,'updated')<>'error' then 'RESEARCH_READY' else 'REFERENCE_ONLY' end,
    'ticker',r.ticker,'snapshot_id',r.snapshot_id,'generated_at',r.generated_at,'as_of_date',r.as_of_date,
    'price_snapshot_status',r.price_snapshot_status,'data_quality',case when v_stale then 'stale' when d.data_quality='error' then 'error' when d.ticker is not null and d.as_of_date<>r.as_of_date then 'stale' else 'updated' end,
    'public_action_allowed',false,'payload',v_payload);
end $$;
revoke all on function public.fetch_stockradar_ai_context(text) from public,anon,authenticated;
grant execute on function public.fetch_stockradar_ai_context(text) to service_role;

-- A bounded server query over the same cache used for ticker analysis.
create or replace function public.query_stockradar_research(p_filter text default 'top',p_sector text default '',p_limit integer default 5)
returns jsonb language plpgsql security definer set search_path=''
as $$
declare v_items jsonb;
begin
  if p_filter not in ('top','pocket_pivot','breakout','near_pivot','sector') then raise exception 'invalid filter'; end if;
  select coalesce(jsonb_agg(public.fetch_stockradar_ai_context(x.ticker)),'[]'::jsonb) into v_items from (
    select r.ticker from private.stock_research_reference_cache r
    left join private.stock_data_snapshots d on d.ticker=r.ticker and d.as_of_date=r.as_of_date and d.data_quality='updated'
      and abs((d.payload->>'price')::numeric-(r.payload#>>'{quote,price}')::numeric)<0.01
    where r.as_of_date >= (now() at time zone 'Asia/Ho_Chi_Minh')::date-4
      and r.generated_at between now()-interval '96 hours' and now()+interval '5 minutes'
      and upper(r.price_snapshot_status) !~ 'STALE|INVALID|FAILED'
      and (p_sector='' or coalesce(r.payload->>'sector','') ilike '%'||left(p_sector,80)||'%')
      and coalesce((d.payload#>>'{technical_detail,vol20}')::numeric,0)>=500000
      and (p_filter in ('top','sector')
        or (p_filter='pocket_pivot' and coalesce(r.payload#>>'{setup,candidate_setup}','') ilike '%POCKET%')
        or (p_filter='breakout' and coalesce(r.payload#>>'{setup,candidate_setup}','') ilike '%BREAKOUT%')
        or (p_filter='near_pivot' and (d.payload#>>'{technical_detail,distance_to_pivot_pct}')::numeric between -5 and 0))
    order by (r.payload#>>'{scores,radar_score_v7}')::numeric desc nulls last,r.ticker
    limit least(greatest(p_limit,1),10)
  ) x;
  return jsonb_build_object('status','READY','items',v_items,'scope','HOSE','public_action_allowed',false);
end $$;
revoke all on function public.query_stockradar_research(text,text,integer) from public,anon,authenticated;
grant execute on function public.query_stockradar_research(text,text,integer) to service_role;

create or replace function private.stockradar_effective_tier(p_user_id uuid)
returns text language sql stable security definer set search_path=''
as $$
 select case when p.account_status<>'ACTIVE' then 'INACTIVE'
   when p.account_tier='PAID'
     and exists(select 1 from private.subscription_grants where user_id=p.id)
     and not exists(select 1 from private.current_paid_entitlements where user_id=p.id) then 'FREE'
   else p.account_tier end from public.profiles p where p.id=p_user_id;
$$;
revoke all on function private.stockradar_effective_tier(uuid) from public,anon,authenticated;

create or replace function public.get_my_stockradar_access()
returns jsonb language plpgsql security definer set search_path=''
as $$
declare v_uid uuid:=auth.uid(); v_tier text; v_count integer:=0; v_paid_until timestamptz;
begin
  if v_uid is null then raise exception 'authentication required' using errcode='42501'; end if;
  v_tier:=private.stockradar_effective_tier(v_uid);
  select request_count into v_count from private.stock_api_rate_limit_windows
    where user_id=v_uid and bucket='stock_ai' and (window_started_at at time zone 'Asia/Ho_Chi_Minh')::date=(now() at time zone 'Asia/Ho_Chi_Minh')::date;
  select paid_until into v_paid_until from private.current_paid_entitlements where user_id=v_uid;
  return jsonb_build_object('account_tier',v_tier,'tier',case when v_tier in ('PAID','TRIAL') then 'pro' else lower(v_tier) end,
    'account_status',case when v_tier='INACTIVE' then 'INACTIVE' else 'ACTIVE' end,
    'expires_at',v_paid_until,'quota',jsonb_build_object('unlimited',v_tier in ('PAID','TRIAL'),
      'limit',case when v_tier in ('PAID','TRIAL') then null else 10 end,
      'remaining',case when v_tier in ('PAID','TRIAL') then null else greatest(10-coalesce(v_count,0),0) end));
end $$;
revoke all on function public.get_my_stockradar_access() from public,anon;
grant execute on function public.get_my_stockradar_access() to authenticated;

-- Keep the StockRadar AI access contract stable across fresh deployments:
-- Guest quota is handled separately by consume_stockradar_guest_ai_quota.
-- Free: 10 successful StockRadar AI requests per Vietnam calendar day.
-- Paid: unlimited StockRadar AI while the account is ACTIVE.
-- Trial/other buckets: retain their configured rolling-window policies.

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

  select private.stockradar_effective_tier(p.id), p.account_status
    into v_tier, v_status
  from public.profiles p
  where p.id = p_user_id;

  if v_status <> 'ACTIVE' or v_tier is null then
    return jsonb_build_object('allowed', false, 'reason', 'ACCOUNT_INACTIVE');
  end if;

  if v_tier in ('PAID','TRIAL') and p_bucket = 'stock_ai' then
    return jsonb_build_object(
      'allowed', true,
      'unlimited', true,
      'limit', null,
      'remaining', null,
      'window_seconds', null,
      'daily_reset_timezone', 'Asia/Ho_Chi_Minh',
      'reset_at', null,
      'retry_after', 0
    );
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
