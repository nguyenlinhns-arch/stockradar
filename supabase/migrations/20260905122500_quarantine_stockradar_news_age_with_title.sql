-- When a legacy news title is cross-ticker, quarantine its paired age field too.
-- This keeps AI-only context from inheriting freshness metadata from the wrong ticker.

create or replace function private.sanitize_stockradar_research_payload(
  p_payload jsonb,
  p_ticker text
)
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

  if v_title ~ '^[A-Z]{3}:' then
    v_prefix := upper(substring(v_title from 1 for 3));
    if v_prefix <> upper(p_ticker) then
      v_payload := jsonb_set(
        v_payload,
        '{research_v7,latest_news_title}',
        'null'::jsonb,
        true
      );
      v_payload := jsonb_set(
        v_payload,
        '{research_v7,latest_news_age_days}',
        'null'::jsonb,
        true
      );
    end if;
  end if;

  return v_payload;
end;
$$;

-- Repair the current affected snapshot detected on 2026-09-05.
update private.stock_research_cache
set payload = jsonb_set(
      payload,
      '{research_v7,latest_news_age_days}',
      'null'::jsonb,
      true
    ),
    updated_at = updated_at
where ticker in ('FPT', 'EIB')
  and payload #>> '{research_v7,latest_news_title}' is null;

update private.stock_research_reference_cache
set payload = jsonb_set(
      payload,
      '{research_v7,latest_news_age_days}',
      'null'::jsonb,
      true
    ),
    updated_at = updated_at
where ticker in ('FPT', 'EIB', 'PGD', 'TCT')
  and payload #>> '{research_v7,latest_news_title}' is null;
