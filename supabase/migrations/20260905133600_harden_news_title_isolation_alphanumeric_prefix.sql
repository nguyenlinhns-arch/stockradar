create or replace function private.sanitize_stockradar_research_payload(p_payload jsonb, p_ticker text)
returns jsonb
language plpgsql
immutable
set search_path = pg_catalog, private
as $$
declare
  v_payload jsonb := p_payload;
  v_title text;
  v_prefix text;
begin
  if v_payload is null or p_ticker is null then
    return v_payload;
  end if;

  v_title := nullif(btrim(v_payload #>> '{research_v7,latest_news_title}'), '');
  if v_title is null then
    return v_payload;
  end if;

  if v_title ~ '^[A-Z0-9]{2,5}:' then
    v_prefix := upper(split_part(v_title, ':', 1));
    if v_prefix <> upper(p_ticker) and v_prefix <> 'HOSE' then
      v_payload := jsonb_set(v_payload, '{research_v7,latest_news_title}', 'null'::jsonb, true);
      v_payload := jsonb_set(v_payload, '{research_v7,latest_news_age_days}', 'null'::jsonb, true);
    end if;
  end if;

  return v_payload;
end;
$$;

update private.stock_research_cache
set payload = private.sanitize_stockradar_research_payload(payload, ticker),
    updated_at = now()
where (payload #>> '{research_v7,latest_news_title}') ~ '^[A-Z0-9]{2,5}:'
  and upper(split_part(payload #>> '{research_v7,latest_news_title}', ':', 1)) not in (upper(ticker), 'HOSE');

update private.stock_research_reference_cache
set payload = private.sanitize_stockradar_research_payload(payload, ticker),
    updated_at = now()
where (payload #>> '{research_v7,latest_news_title}') ~ '^[A-Z0-9]{2,5}:'
  and upper(split_part(payload #>> '{research_v7,latest_news_title}', ':', 1)) not in (upper(ticker), 'HOSE');
