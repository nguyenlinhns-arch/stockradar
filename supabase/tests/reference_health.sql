-- Run against a seeded StockRadar project. All temporary timestamp changes roll back.
begin;

do $test$
declare v_health jsonb := public.stockradar_runtime_health_snapshot();
begin
  if (v_health #>> '{ai_reference,total_rows}')::int = 0 then
    raise exception 'reference_health requires the existing reference cache';
  end if;
  if (v_health #>> '{research,total_rows}')::int = 0
     and v_health #>> '{capabilities,ai_answer_coverage}' = 'READY_405_OF_405'
     and v_health->>'overall_status' <> 'REFERENCE_ONLY_RESEARCH_BLOCKED' then
    raise exception 'reference coverage must not claim research is ready';
  end if;
  if has_function_privilege('anon','public.stockradar_runtime_health_snapshot()','execute')
     or has_function_privilege('authenticated','public.stockradar_runtime_health_snapshot()','execute') then
    raise exception 'private runtime diagnostics must remain service-role only';
  end if;
end $test$;

savepoint reference_baseline;
update private.stock_research_reference_cache set generated_at = now() + interval '1 hour';
do $test$
declare v_health jsonb := public.stockradar_runtime_health_snapshot();
begin
  if (v_health #>> '{ai_reference,fresh_rows}')::int <> 0
     or v_health->>'overall_status' <> 'AI_COVERAGE_DEGRADED' then
    raise exception 'future generated_at must block coverage';
  end if;
end $test$;
rollback to savepoint reference_baseline;

update private.stock_research_reference_cache
set as_of_date = (now() at time zone 'Asia/Ho_Chi_Minh')::date + 1;
do $test$
declare v_health jsonb := public.stockradar_runtime_health_snapshot();
begin
  if (v_health #>> '{ai_reference,fresh_rows}')::int <> 0 then
    raise exception 'future source dates must not count as fresh';
  end if;
end $test$;
rollback to savepoint reference_baseline;

update private.stock_research_reference_cache
set as_of_date = (now() at time zone 'Asia/Ho_Chi_Minh')::date - 5;
do $test$
declare v_health jsonb := public.stockradar_runtime_health_snapshot();
begin
  if (v_health #>> '{ai_reference,fresh_rows}')::int <> 0 then
    raise exception 'old source dates must not become fresh through regeneration';
  end if;
end $test$;
rollback;
