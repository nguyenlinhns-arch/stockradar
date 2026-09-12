create or replace function public.resolve_stockradar_project_research_context(p_question text)
returns jsonb
language plpgsql
security definer
set search_path to ''
as $function$
declare
  token text;
  candidate text;
  raw jsonb;
  compact jsonb;
  primary_context jsonb := null;
  related_contexts jsonb := '[]'::jsonb;
  tickers text[] := '{}'::text[];
  primary_ticker text := null;
  primary_snapshot text := null;
  primary_as_of text := null;
  primary_grade text := null;
begin
  if p_question is null or length(btrim(p_question))=0 then
    return jsonb_build_object('linked',false);
  end if;

  for token in
    select x
    from regexp_split_to_table(
      regexp_replace(left(p_question,8000),'[^A-Za-z0-9$#]+',' ','g'),
      E'\\s+'
    ) as x
  loop
    candidate := upper(trim(both '$#' from token));
    if length(candidate)<>3 or candidate !~ '[A-Z]' then continue; end if;
    if candidate = any(array[
      'VPA','VCP','EPS','ROE','ROA','PBT','FCF','DCF','ATR','RSI','MAC','PEG','MOS','GDP','CPI','USD','VND','ETF','NAV','IPO','API','OTP','JWT','URL','CEO','CFO','CTO','LLM','MAI',
      'CHI','CHO','GHI','TRA','SAU','TIN','RUI','MOC','MOI','TOP','MUA','BAN','GIU','GIA','NAY','SAO','KHI','NEU','HAY','DAI','HAN','VON','LOI','ROI','THE','NAO','CAN','XEM','HOM','CAC','CUA','VOI','TAI','TOI','NEN','CON','HON','GAN','LAM','VAN','QUA','MOT','HAI','NAM','DAY','DAU','TEN','BAO','LAI','LUC','NOI','NHA','DON','GON','RAT','TAM','TAN','CHU','DAN','DEN','CAP','NET','DAT','TUC','TIE','COI','FOR','AND','NEW','NOW','ALL','GET','SET'
    ]) then continue; end if;
    if candidate = any(tickers) then continue; end if;

    raw := public.fetch_stockradar_ai_context(candidate);
    if coalesce(raw->>'status','') not in ('INTERNAL_RESEARCH_READY','INTERNAL_REFERENCE_READY') then
      continue;
    end if;

    compact := jsonb_strip_nulls(jsonb_build_object(
      'status',raw->>'status',
      'context_grade',raw->>'context_grade',
      'ticker',raw->>'ticker',
      'snapshot_id',raw->>'snapshot_id',
      'generated_at',raw->>'generated_at',
      'as_of_date',raw->>'as_of_date',
      'price_snapshot_status',raw->>'price_snapshot_status',
      'data_quality',raw->>'data_quality',
      'data_layer_status',raw->>'data_layer_status',
      'public_action_allowed',false,
      'sector',raw#>>'{payload,sector}',
      'business_bucket',raw#>>'{payload,business_bucket}',
      'company_type',raw#>>'{payload,company_type}',
      'volume_mode',raw#>>'{payload,volume_mode}',
      'quote',raw#>'{payload,quote}',
      'market_context',raw#>'{payload,market_context}',
      'setup',raw#>'{payload,setup}',
      'scores',raw#>'{payload,scores}',
      'risk',raw#>'{payload,risk}',
      'technical_detail',raw#>'{payload,technical_detail}',
      'fundamental_detail',raw#>'{payload,fundamental_detail}',
      'valuation_detail',raw#>'{payload,valuation_detail}',
      'fundamental_valuation',raw#>'{payload,fundamental_valuation}',
      'catalyst',raw#>'{payload,catalyst}',
      'corporate_action',raw#>'{payload,corporate_action}',
      'supply_institutional',raw#>'{payload,supply_institutional}',
      'trade_plan',raw#>'{payload,trade_plan}',
      'release',raw#>'{payload,release}',
      'research_v7',raw#>'{payload,research_v7}'
    ));

    tickers := array_append(tickers,raw->>'ticker');
    if primary_context is null then
      primary_context := compact;
      primary_ticker := raw->>'ticker';
      primary_snapshot := raw->>'snapshot_id';
      primary_as_of := raw->>'as_of_date';
      primary_grade := raw->>'context_grade';
    else
      related_contexts := related_contexts || jsonb_build_array(compact);
    end if;

    exit when coalesce(array_length(tickers,1),0) >= 4;
  end loop;

  if primary_context is null then
    return jsonb_build_object('linked',false);
  end if;

  primary_context := primary_context || jsonb_build_object(
    'linked_tickers',to_jsonb(tickers),
    'related_contexts',related_contexts
  );

  return jsonb_build_object(
    'linked',true,
    'ticker',primary_ticker,
    'tickers',to_jsonb(tickers),
    'snapshot_id',primary_snapshot,
    'as_of_date',primary_as_of,
    'context_grade',primary_grade,
    'context',primary_context
  );
end
$function$;

revoke all on function public.resolve_stockradar_project_research_context(text) from public, anon, authenticated;
grant execute on function public.resolve_stockradar_project_research_context(text) to service_role;