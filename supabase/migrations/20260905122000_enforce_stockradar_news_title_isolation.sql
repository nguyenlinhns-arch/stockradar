-- Prevent cross-ticker legacy news titles from entering AI research caches.
-- This is an internal cache-isolation control only; it does not enable any public data/API path.

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

  -- Stock tickers in this internal HOSE research cache are three letters.
  -- A different three-letter prefix is treated as cross-ticker contamination.
  if v_title ~ '^[A-Z]{3}:' then
    v_prefix := upper(substring(v_title from 1 for 3));
    if v_prefix <> upper(p_ticker) then
      v_payload := jsonb_set(
        v_payload,
        '{research_v7,latest_news_title}',
        'null'::jsonb,
        true
      );
    end if;
  end if;

  return v_payload;
end;
$$;

revoke all on function private.sanitize_stockradar_research_payload(jsonb, text)
  from public, anon, authenticated;

create or replace function private.enforce_stockradar_news_title_isolation()
returns trigger
language plpgsql
set search_path = pg_catalog, private
as $$
begin
  new.payload := private.sanitize_stockradar_research_payload(new.payload, new.ticker);
  return new;
end;
$$;

revoke all on function private.enforce_stockradar_news_title_isolation()
  from public, anon, authenticated;

drop trigger if exists trg_stock_research_cache_news_title_isolation
  on private.stock_research_cache;
create trigger trg_stock_research_cache_news_title_isolation
before insert or update of ticker, payload
on private.stock_research_cache
for each row execute function private.enforce_stockradar_news_title_isolation();

drop trigger if exists trg_stock_research_reference_cache_news_title_isolation
  on private.stock_research_reference_cache;
create trigger trg_stock_research_reference_cache_news_title_isolation
before insert or update of ticker, payload
on private.stock_research_reference_cache
for each row execute function private.enforce_stockradar_news_title_isolation();

-- Repair any already-cached cross-ticker titles without changing the rest of the payload.
update private.stock_research_cache
set payload = private.sanitize_stockradar_research_payload(payload, ticker),
    updated_at = updated_at
where payload #>> '{research_v7,latest_news_title}' ~ '^[A-Z]{3}:'
  and upper(substring(payload #>> '{research_v7,latest_news_title}' from 1 for 3)) <> upper(ticker);

update private.stock_research_reference_cache
set payload = private.sanitize_stockradar_research_payload(payload, ticker),
    updated_at = updated_at
where payload #>> '{research_v7,latest_news_title}' ~ '^[A-Z]{3}:'
  and upper(substring(payload #>> '{research_v7,latest_news_title}' from 1 for 3)) <> upper(ticker);
