-- Signed-in research screen, using the same observations as StockRadar AI.
-- This bounded projection grants neither table access nor action publication.
create or replace function public.get_stockradar_radar_v1()
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_uid uuid := auth.uid();
  v_snapshot text; v_generated timestamptz; v_date date;
  v_items jsonb; v_status jsonb;
begin
  if v_uid is null or not exists (
    select 1 from public.profiles where id=v_uid and account_status='ACTIVE'
  ) then
    raise exception 'Active account required' using errcode='42501';
  end if;
  select snapshot_id, generated_at, as_of_date into v_snapshot,v_generated,v_date
  from private.stock_research_reference_cache
  order by as_of_date desc,generated_at desc,snapshot_id limit 1;
  v_status := public.get_stockradar_recommendation_status_v1();
  with observations as (
    select r.*,
      coalesce(r.generated_at between now()-interval '96 hours' and now()+interval '5 minutes'
        and r.as_of_date between (now() at time zone 'Asia/Ho_Chi_Minh')::date-4
          and (now() at time zone 'Asia/Ho_Chi_Minh')::date
        and upper(r.price_snapshot_status) !~ 'STALE|INVALID|FAILED',false) as fresh,
      d.payload as detail
    from private.stock_research_reference_cache r
    left join private.stock_data_snapshots d on d.ticker=r.ticker
      and d.as_of_date=r.as_of_date and d.data_quality='updated'
      and abs((d.payload->>'price')::numeric-(r.payload#>>'{quote,price}')::numeric)<0.01
    where r.snapshot_id=v_snapshot
  ), projected as (
    select ticker, jsonb_build_object(
      'ticker',ticker,'sector',coalesce(payload->>'sector','Chưa phân ngành'),
      'price',payload#>'{quote,price}','as_of_date',as_of_date,
      'fresh',fresh,'research_ready',research_ready and fresh,
      'score',case when research_ready and fresh then payload#>'{scores,radar_score_v7}' else null end,
      'setup',payload#>>'{setup,candidate_setup}',
      'initial_setup',payload#>>'{setup,candidate_setup}' in ('POCKET_PIVOT','EARLY_BREAKOUT','CONFIRMED_BREAKOUT','RETEST'),
      'new_buy_allowed',fresh and exists(select 1 from jsonb_array_elements(v_status->'items') b where b->>'ticker'=observations.ticker and b->>'publish_status'='PUBLISHED'),
      'scores',jsonb_build_object('business',payload#>'{scores,fundamental_domain_score_v4}',
        'technical',payload#>'{scores,technical_score}','flow',payload#>'{scores,flow_score_v4}'),
      'technical',jsonb_build_object('change_pct',detail#>'{technical_detail,pct_change}',
        'ma20',detail#>'{technical_detail,ma20}','ma50',detail#>'{technical_detail,ma50}',
        'ma200',detail#>'{technical_detail,ma200}','pivot',detail#>'{technical_detail,pivot20}',
        'volume',detail#>'{quote,volume}','volume20',detail#>'{technical_detail,vol20}'),
      'business',jsonb_build_object('roe_pct',detail#>'{fundamental_detail,roe_ttm_pct}',
        'period',detail#>'{fundamental_detail,period_end}','eps_growth_pct',detail#>'{fundamental_detail,eps_growth_yoy_pct}',
        'profit_growth_pct',detail#>'{fundamental_detail,profit_growth_yoy_pct}',
        'pbt_growth_pct',detail#>'{fundamental_detail,pbt_growth_yoy_pct}'),
      'sector_strength',payload#>'{scores,sector_strength_score}'
    ) as item from observations
  ) select coalesce(jsonb_agg(item order by (item->>'research_ready')::boolean desc,
      (item->>'score')::numeric desc nulls last,ticker),'[]'::jsonb) into v_items from projected;
  return jsonb_build_object('schema_version','STOCKRADAR_RESEARCH_RADAR_V1','mode','RESEARCH_SCREEN',
    'snapshot',jsonb_build_object('id',v_snapshot,'as_of_date',v_date,'evaluated_at',v_generated),
    'checked_at',now(),'items',v_items,
    'coverage',jsonb_build_object('total',jsonb_array_length(v_items),
      'research_ready',(select count(*) from jsonb_array_elements(v_items) r where r->>'research_ready'='true'),
      'initial_setups',(select count(*) from jsonb_array_elements(v_items) r where r->>'initial_setup'='true'),
      'published_buys',(select count(*) from jsonb_array_elements(v_items) r where r->>'new_buy_allowed'='true')),
    'schedule',v_status->'schedule');
end $$;
revoke all on function public.get_stockradar_radar_v1() from public,anon,authenticated;
grant execute on function public.get_stockradar_radar_v1() to authenticated;
