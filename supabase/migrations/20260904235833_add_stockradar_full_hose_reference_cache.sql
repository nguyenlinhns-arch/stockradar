create table if not exists private.stock_research_reference_cache (
  ticker text primary key check (length(ticker)=3 and ticker ~ '^[A-Z0-9]{3}$' and ticker ~ '[A-Z]'),
  snapshot_id text not null,
  generated_at timestamptz not null,
  as_of_date date not null,
  data_role text not null default 'INTERNAL_REFERENCE',
  price_snapshot_status text not null,
  payload jsonb not null,
  source_ref text not null,
  research_ready boolean not null default false,
  updated_at timestamptz not null default now()
);

alter table private.stock_research_reference_cache enable row level security;
revoke all on private.stock_research_reference_cache from public, anon, authenticated;

create or replace function public.upsert_stockradar_internal_reference_context(
  p_ticker text,
  p_snapshot_id text,
  p_generated_at timestamptz,
  p_as_of_date date,
  p_price_snapshot_status text,
  p_payload jsonb,
  p_source_ref text,
  p_research_ready boolean default false
) returns void
language plpgsql security definer set search_path=''
as $$
declare v_ticker text := upper(trim(coalesce(p_ticker,'')));
begin
  if length(v_ticker)<>3 or v_ticker !~ '^[A-Z0-9]{3}$' or v_ticker !~ '[A-Z]' then raise exception 'invalid ticker'; end if;
  if p_payload is null or jsonb_typeof(p_payload) <> 'object' then raise exception 'payload object required'; end if;
  if coalesce((p_payload #>> '{release,public_action_allowed}')::boolean,false) is true then raise exception 'public action must be false'; end if;
  insert into private.stock_research_reference_cache(ticker,snapshot_id,generated_at,as_of_date,data_role,price_snapshot_status,payload,source_ref,research_ready,updated_at)
  values(v_ticker,trim(p_snapshot_id),p_generated_at,p_as_of_date,'INTERNAL_REFERENCE',trim(p_price_snapshot_status),p_payload,trim(p_source_ref),coalesce(p_research_ready,false),now())
  on conflict(ticker) do update set snapshot_id=excluded.snapshot_id,generated_at=excluded.generated_at,as_of_date=excluded.as_of_date,data_role=excluded.data_role,price_snapshot_status=excluded.price_snapshot_status,payload=excluded.payload,source_ref=excluded.source_ref,research_ready=excluded.research_ready,updated_at=now();
end $$;

create or replace function public.prune_stockradar_internal_reference_context(p_allowed_tickers text[])
returns integer language plpgsql security definer set search_path=''
as $$
declare v_count integer;
begin
  delete from private.stock_research_reference_cache where not (ticker=any(coalesce(p_allowed_tickers,array[]::text[])));
  get diagnostics v_count=row_count;
  return v_count;
end $$;

create or replace function public.fetch_stockradar_ai_context(p_ticker text)
returns jsonb language plpgsql security definer set search_path=''
as $$
declare
  v_ticker text:=upper(trim(coalesce(p_ticker,'')));
  r private.stock_research_cache%rowtype;
  x private.stock_research_reference_cache%rowtype;
  v_status text;
begin
  if length(v_ticker)<>3 or v_ticker !~ '^[A-Z0-9]{3}$' or v_ticker !~ '[A-Z]' then return jsonb_build_object('status','INVALID_REQUEST','reason','INVALID_TICKER'); end if;
  select * into r from private.stock_research_cache where ticker=v_ticker;
  if r.ticker is not null and now()-r.generated_at<=interval '96 hours' then
    v_status:=upper(trim(coalesce(r.price_snapshot_status,'')));
    if v_status not like '%STALE%' and v_status not like '%INVALID%' and v_status not like '%FAILED%' then
      return jsonb_build_object('status','INTERNAL_RESEARCH_READY','context_grade','RESEARCH_READY','ticker',r.ticker,'snapshot_id',r.snapshot_id,'generated_at',r.generated_at,'as_of_date',r.as_of_date,'data_role',r.data_role,'price_snapshot_status',r.price_snapshot_status,'public_action_allowed',false,'source_ref',r.source_ref,'payload',r.payload);
    end if;
  end if;
  select * into x from private.stock_research_reference_cache where ticker=v_ticker;
  if x.ticker is null then return jsonb_build_object('status','NOT_FOUND','ticker',v_ticker); end if;
  v_status:=upper(trim(coalesce(x.price_snapshot_status,'')));
  if now()-x.generated_at>interval '96 hours' or v_status like '%STALE%' or v_status like '%INVALID%' or v_status like '%FAILED%' then
    return jsonb_build_object('status','INTERNAL_REFERENCE_STALE','ticker',x.ticker,'snapshot_id',x.snapshot_id,'generated_at',x.generated_at,'as_of_date',x.as_of_date,'price_snapshot_status',x.price_snapshot_status,'public_action_allowed',false);
  end if;
  return jsonb_build_object('status','INTERNAL_REFERENCE_READY','context_grade','REFERENCE_ONLY','research_ready',x.research_ready,'ticker',x.ticker,'snapshot_id',x.snapshot_id,'generated_at',x.generated_at,'as_of_date',x.as_of_date,'data_role',x.data_role,'price_snapshot_status',x.price_snapshot_status,'public_action_allowed',false,'source_ref',x.source_ref,'payload',x.payload);
end $$;

revoke all on function public.upsert_stockradar_internal_reference_context(text,text,timestamptz,date,text,jsonb,text,boolean) from public,anon,authenticated;
revoke all on function public.prune_stockradar_internal_reference_context(text[]) from public,anon,authenticated;
revoke all on function public.fetch_stockradar_ai_context(text) from public,anon,authenticated;
grant execute on function public.upsert_stockradar_internal_reference_context(text,text,timestamptz,date,text,jsonb,text,boolean) to service_role;
grant execute on function public.prune_stockradar_internal_reference_context(text[]) to service_role;
grant execute on function public.fetch_stockradar_ai_context(text) to service_role;
