create table if not exists private.stock_research_cache (
  ticker text primary key,
  snapshot_id text not null,
  generated_at timestamp with time zone not null,
  as_of_date date not null,
  data_role text not null default 'INTERNAL_RESEARCH',
  price_snapshot_status text not null,
  payload jsonb not null,
  source_ref text not null,
  public_action_allowed boolean not null default false,
  updated_at timestamp with time zone not null default now(),
  constraint stock_research_cache_ticker_check check (length(ticker) = 3 and ticker ~ '^[A-Z0-9]{3}$' and ticker ~ '[A-Z]'),
  constraint stock_research_cache_data_role_check check (data_role = 'INTERNAL_RESEARCH'),
  constraint stock_research_cache_payload_check check (jsonb_typeof(payload) = 'object'),
  constraint stock_research_cache_public_action_check check (public_action_allowed is false)
);

revoke all on table private.stock_research_cache from public, anon, authenticated;
grant usage on schema private to service_role;
grant select, insert, update, delete on table private.stock_research_cache to service_role;

create or replace function public.upsert_stockradar_internal_research_context(
  p_ticker text,
  p_snapshot_id text,
  p_generated_at timestamp with time zone,
  p_as_of_date date,
  p_price_snapshot_status text,
  p_payload jsonb,
  p_source_ref text
)
returns void
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_ticker text := upper(trim(coalesce(p_ticker, '')));
  v_public_flag text := lower(coalesce(p_payload #>> '{release,public_action_allowed}', 'false'));
begin
  if length(v_ticker) <> 3 or v_ticker !~ '^[A-Z0-9]{3}$' or v_ticker !~ '[A-Z]' then
    raise exception 'invalid ticker';
  end if;
  if length(trim(coalesce(p_snapshot_id, ''))) = 0 then
    raise exception 'snapshot_id is required';
  end if;
  if p_generated_at is null or p_as_of_date is null then
    raise exception 'research timestamps are required';
  end if;
  if length(trim(coalesce(p_price_snapshot_status, ''))) = 0 then
    raise exception 'price_snapshot_status is required';
  end if;
  if p_payload is null or jsonb_typeof(p_payload) <> 'object' then
    raise exception 'payload must be a JSON object';
  end if;
  if v_public_flag not in ('false', '') then
    raise exception 'internal research payload cannot be public-action enabled';
  end if;
  if length(trim(coalesce(p_source_ref, ''))) = 0 then
    raise exception 'source_ref is required';
  end if;

  insert into private.stock_research_cache(
    ticker, snapshot_id, generated_at, as_of_date, data_role,
    price_snapshot_status, payload, source_ref, public_action_allowed, updated_at
  ) values (
    v_ticker, trim(p_snapshot_id), p_generated_at, p_as_of_date, 'INTERNAL_RESEARCH',
    trim(p_price_snapshot_status), p_payload, trim(p_source_ref), false, now()
  )
  on conflict (ticker) do update
    set snapshot_id = excluded.snapshot_id,
        generated_at = excluded.generated_at,
        as_of_date = excluded.as_of_date,
        data_role = 'INTERNAL_RESEARCH',
        price_snapshot_status = excluded.price_snapshot_status,
        payload = excluded.payload,
        source_ref = excluded.source_ref,
        public_action_allowed = false,
        updated_at = now();
end;
$function$;

revoke all on function public.upsert_stockradar_internal_research_context(text,text,timestamp with time zone,date,text,jsonb,text) from public, anon, authenticated;
grant execute on function public.upsert_stockradar_internal_research_context(text,text,timestamp with time zone,date,text,jsonb,text) to service_role;

create or replace function public.fetch_stockradar_internal_research_context(p_ticker text)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_ticker text := upper(trim(coalesce(p_ticker, '')));
  v_row private.stock_research_cache%rowtype;
begin
  if length(v_ticker) <> 3 or v_ticker !~ '^[A-Z0-9]{3}$' or v_ticker !~ '[A-Z]' then
    return jsonb_build_object('status', 'INVALID_REQUEST', 'reason', 'INVALID_TICKER');
  end if;

  select * into v_row from private.stock_research_cache where ticker = v_ticker;
  if v_row.ticker is null then
    return jsonb_build_object('status', 'NOT_FOUND', 'ticker', v_ticker);
  end if;

  return jsonb_build_object(
    'status', 'INTERNAL_RESEARCH_READY',
    'ticker', v_row.ticker,
    'snapshot_id', v_row.snapshot_id,
    'generated_at', v_row.generated_at,
    'as_of_date', v_row.as_of_date,
    'data_role', v_row.data_role,
    'price_snapshot_status', v_row.price_snapshot_status,
    'public_action_allowed', false,
    'source_ref', v_row.source_ref,
    'payload', v_row.payload
  );
end;
$function$;

revoke all on function public.fetch_stockradar_internal_research_context(text) from public, anon, authenticated;
grant execute on function public.fetch_stockradar_internal_research_context(text) to service_role;
