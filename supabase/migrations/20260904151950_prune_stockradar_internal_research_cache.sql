create or replace function public.prune_stockradar_internal_research_context(p_allowed_tickers text[])
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_allowed text[] := array[]::text[];
  v_deleted integer := 0;
begin
  if p_allowed_tickers is null then
    raise exception 'p_allowed_tickers is required';
  end if;

  select coalesce(array_agg(distinct upper(trim(ticker)) order by upper(trim(ticker))), array[]::text[])
    into v_allowed
  from unnest(p_allowed_tickers) as u(ticker)
  where length(trim(coalesce(ticker, ''))) > 0;

  if cardinality(v_allowed) > 405 then
    raise exception 'allowed ticker set exceeds canonical HOSE universe';
  end if;

  if exists (
    select 1
    from unnest(v_allowed) as u(ticker)
    where length(ticker) <> 3
       or ticker !~ '^[A-Z0-9]{3}$'
       or ticker !~ '[A-Z]'
  ) then
    raise exception 'allowed ticker set contains invalid ticker';
  end if;

  delete from private.stock_research_cache
  where not (upper(trim(ticker)) = any(v_allowed));

  get diagnostics v_deleted = row_count;
  return v_deleted;
end;
$$;

revoke all on function public.prune_stockradar_internal_research_context(text[]) from public;
revoke all on function public.prune_stockradar_internal_research_context(text[]) from anon;
revoke all on function public.prune_stockradar_internal_research_context(text[]) from authenticated;
grant execute on function public.prune_stockradar_internal_research_context(text[]) to service_role;
