create or replace function public.fetch_stockradar_ai_context(p_ticker text)
returns jsonb
language plpgsql
security definer
set search_path to ''
as $function$
declare
  r record;
  d private.stock_data_snapshots%rowtype;
  v_payload jsonb;
  v_stale boolean;
  v_data_layer_status text := 'NO_FRESH_MATCH';
  v_data_price_text text;
  v_research_price_text text;
  v_legacy_news_title text;
begin
  select * into r
  from (
    select ticker, snapshot_id, generated_at, as_of_date, price_snapshot_status,
           payload, source_ref, true as ready, 2 as source_priority
      from private.stock_research_cache
     where ticker = upper(trim(p_ticker))
    union all
    select ticker, snapshot_id, generated_at, as_of_date, price_snapshot_status,
           payload, source_ref, research_ready as ready, 1 as source_priority
      from private.stock_research_reference_cache
     where ticker = upper(trim(p_ticker))
  ) q
  order by as_of_date desc, generated_at desc, ready desc, source_priority desc
  limit 1;

  if r.ticker is null then
    return jsonb_build_object('status','NOT_FOUND','ticker',upper(trim(p_ticker)));
  end if;

  v_stale := r.generated_at > now() + interval '5 minutes'
    or r.generated_at < now() - interval '96 hours'
    or r.as_of_date > (now() at time zone 'Asia/Ho_Chi_Minh')::date
    or r.as_of_date < (now() at time zone 'Asia/Ho_Chi_Minh')::date - 4
    or upper(r.price_snapshot_status) ~ 'STALE|INVALID|FAILED';

  v_payload := r.payload;

  -- AI-only safety boundary: legacy latest_news_title may come from a broad
  -- recall feed. If the title carries an explicit ticker prefix that does not
  -- match the requested ticker, quarantine it before any model/renderer sees it.
  -- Official ticker-scoped catalyst fields remain untouched.
  v_legacy_news_title := v_payload#>>'{research_v7,latest_news_title}';
  if coalesce(v_legacy_news_title,'') ~ '^[A-Z0-9]{3}:'
     and split_part(v_legacy_news_title,':',1) <> r.ticker then
    v_payload := jsonb_set(v_payload,'{research_v7,latest_news_title}','null'::jsonb,true);
    v_payload := jsonb_set(v_payload,'{research_v7,latest_news_age_days}','null'::jsonb,true);
  end if;

  -- The structured data layer is optional enrichment only. Never allow an
  -- older/error enrichment row to downgrade an otherwise-fresh Research V7
  -- record. Select only the newest row aligned to the same research date and
  -- explicitly marked updated.
  select * into d
    from private.stock_data_snapshots
   where ticker = r.ticker
     and as_of_date = r.as_of_date
     and data_quality = 'updated'
   order by imported_at desc
   limit 1;

  if d.ticker is not null then
    v_data_price_text := d.payload->>'price';
    v_research_price_text := r.payload#>>'{quote,price}';

    if coalesce(v_data_price_text,'') ~ '^-?[0-9]+([.][0-9]+)?$'
       and coalesce(v_research_price_text,'') ~ '^-?[0-9]+([.][0-9]+)?$' then
      if abs(v_data_price_text::numeric - v_research_price_text::numeric) < 0.01 then
        v_payload := v_payload || jsonb_build_object(
          'technical_detail', d.payload->'technical_detail',
          'fundamental_detail', d.payload->'fundamental_detail',
          'valuation_detail', d.payload->'valuation_detail',
          'history', d.payload->'history',
          'data_quality', d.data_quality,
          'volume_mode', 'EOD',
          'data_snapshot_id', d.snapshot_id,
          'quote', coalesce(r.payload->'quote','{}'::jsonb) || coalesce(d.payload->'quote','{}'::jsonb)
        );
        v_data_layer_status := 'ENRICHED';
      else
        v_data_layer_status := 'PRICE_MISMATCH';
      end if;
    else
      v_data_layer_status := 'MISSING_OR_INVALID_PRICE';
    end if;
  end if;

  return jsonb_build_object(
    'status', case when r.ready then 'INTERNAL_RESEARCH_READY' else 'INTERNAL_REFERENCE_READY' end,
    'context_grade', case when r.ready and not v_stale then 'RESEARCH_READY' else 'REFERENCE_ONLY' end,
    'ticker', r.ticker,
    'snapshot_id', r.snapshot_id,
    'generated_at', r.generated_at,
    'as_of_date', r.as_of_date,
    'price_snapshot_status', r.price_snapshot_status,
    'data_quality', case when v_stale then 'stale' else 'updated' end,
    'data_layer_status', v_data_layer_status,
    'public_action_allowed', false,
    'payload', v_payload
  );
end
$function$;
