-- Fail closed when internal research is stale or explicitly marked stale/invalid/failed.
-- Keeps recent Friday data usable through the weekend while preventing old snapshots
-- from being presented by StockRadar AI as current market context.

create or replace function public.fetch_stockradar_internal_research_context(p_ticker text)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_ticker text := upper(trim(coalesce(p_ticker, '')));
  v_row private.stock_research_cache%rowtype;
  v_age interval;
  v_price_status text;
  v_fresh boolean;
begin
  if length(v_ticker) <> 3 or v_ticker !~ '^[A-Z0-9]{3}$' or v_ticker !~ '[A-Z]' then
    return jsonb_build_object('status', 'INVALID_REQUEST', 'reason', 'INVALID_TICKER');
  end if;

  select * into v_row from private.stock_research_cache where ticker = v_ticker;
  if v_row.ticker is null then
    return jsonb_build_object('status', 'NOT_FOUND', 'ticker', v_ticker);
  end if;

  v_age := now() - v_row.generated_at;
  v_price_status := upper(trim(coalesce(v_row.price_snapshot_status, '')));
  v_fresh := v_age <= interval '96 hours'
             and v_price_status not like '%STALE%'
             and v_price_status not like '%INVALID%'
             and v_price_status not like '%FAILED%';

  if not v_fresh then
    return jsonb_build_object(
      'status', 'INTERNAL_RESEARCH_STALE',
      'reason', case
        when v_age > interval '96 hours' then 'RESEARCH_OLDER_THAN_96H'
        when v_price_status like '%STALE%' then 'PRICE_SNAPSHOT_STALE'
        when v_price_status like '%INVALID%' then 'PRICE_SNAPSHOT_INVALID'
        when v_price_status like '%FAILED%' then 'PRICE_SNAPSHOT_FAILED'
        else 'RESEARCH_FRESHNESS_BLOCKED'
      end,
      'ticker', v_row.ticker,
      'snapshot_id', v_row.snapshot_id,
      'generated_at', v_row.generated_at,
      'as_of_date', v_row.as_of_date,
      'price_snapshot_status', v_row.price_snapshot_status,
      'public_action_allowed', false,
      'source_ref', v_row.source_ref
    );
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
