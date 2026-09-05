-- Daily bulletin uses the same allowlisted public report status as the homepage.
-- The existing action-alert workflow remains responsible for intraday transitions.
create or replace function private.enqueue_stockradar_daily_briefs_v1(p_at timestamptz default now())
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_local timestamp := p_at at time zone 'Asia/Ho_Chi_Minh';
  v_status jsonb; v_payload jsonb; v_key text; v_id uuid;
  v_scheduled timestamptz; v_enqueued integer := 0; r record;
begin
  if extract(isodow from v_local) not between 1 and 5 or v_local::time < time '09:00' or v_local::time >= time '09:30' then
    return jsonb_build_object('status','OUTSIDE_DAILY_WINDOW','enqueued',0);
  end if;
  perform pg_advisory_xact_lock(hashtextextended('stockradar-daily-brief-v1',0));
  v_status := public.get_stockradar_recommendation_status_v1();
  if coalesce(v_status#>>'{email,ready}','false') <> 'true' then
    return jsonb_build_object('status','EMAIL_DISABLED','enqueued',0);
  end if;
  if coalesce(v_status#>>'{snapshot,fresh}','false') <> 'true' then
    return jsonb_build_object('status','NO_FRESH_REVIEW','enqueued',0);
  end if;
  v_scheduled := (v_local::date + time '09:00') at time zone 'Asia/Ho_Chi_Minh';
  v_payload := jsonb_build_object('subject','[StockRadar] Bản tin cổ phiếu ' || to_char(v_local::date,'DD/MM/YYYY'),
    'headline',case when jsonb_array_length(v_status->'items')>0 then jsonb_array_length(v_status->'items') || ' mã được xác nhận mua' else 'Chưa có mã được xác nhận mua' end,
    'report_date',v_local::date,'generated_at',p_at,'evaluated_at',v_status#>'{snapshot,evaluated_at}',
    'next_review_at',v_status#>'{schedule,next_review_at}','opportunities',v_status->'items',
    'watchlist_changes','[]'::jsonb,'coverage',v_status->'coverage',
    'action_snapshot_id',(select active_snapshot_id from private.stock_api_gate where singleton),
    'action_manifest_ref',(select active_manifest_ref from private.stock_api_gate where singleton));
  for r in select e.user_id from private.product_email_eligibility e
    join auth.users u on u.id=e.user_id and u.email_confirmed_at is not null
    where e.eligible_to_send and e.daily_brief
  loop
    v_key := 'daily-v1-' || md5(r.user_id::text || '|' || v_local::date::text);
    if exists(select 1 from private.email_outbox where idempotency_key=v_key) then continue; end if;
    v_id := public.enqueue_stockradar_email_v2(r.user_id,'DAILY_BRIEF',v_key,
      v_status#>>'{snapshot,snapshot_id}',v_payload,v_scheduled,v_scheduled+interval '2 hours',30,'daily:' || v_local::date::text);
    if v_id is not null then v_enqueued := v_enqueued+1; end if;
  end loop;
  return jsonb_build_object('status','PROCESSED','enqueued',v_enqueued,'scheduled_at',v_scheduled);
end;
$$;
revoke all on function private.enqueue_stockradar_daily_briefs_v1(timestamptz) from public,anon,authenticated;

-- A bounded retry window tolerates temporary database/data-refresh delays. The
-- date+recipient unique key prevents duplicate bulletins across retries.
select cron.schedule('stockradar-daily-brief-v1','*/2 2 * * 1-5',
  'select private.enqueue_stockradar_daily_briefs_v1();');
