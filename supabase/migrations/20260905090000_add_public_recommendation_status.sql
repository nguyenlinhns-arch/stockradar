-- Public operational summary and explicitly released buy reports only. No recipients,
-- watchlists, raw source payloads, credentials or internal ranking lists are exposed.
create or replace function private.stockradar_next_weekday_checkpoint(
  p_after timestamptz, p_times time[]
) returns timestamptz language sql stable set search_path = '' as $$
  select min((d::date + t) at time zone 'Asia/Ho_Chi_Minh')
  from generate_series((p_after at time zone 'Asia/Ho_Chi_Minh')::date::timestamp,
    (p_after at time zone 'Asia/Ho_Chi_Minh')::date + interval '8 days', interval '1 day') d
  cross join unnest(p_times) t
  where extract(isodow from d) between 1 and 5
    and (d::date + t) at time zone 'Asia/Ho_Chi_Minh' > p_after;
$$;
revoke all on function private.stockradar_next_weekday_checkpoint(timestamptz,time[]) from public,anon,authenticated;

create or replace function public.get_stockradar_recommendation_status_v1()
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_gate private.stock_api_gate%rowtype;
  v_email private.email_delivery_gate%rowtype;
  v_scheduler private.email_worker_scheduler_gate%rowtype;
  v_snapshot text; v_generated timestamptz; v_date date;
  v_total integer := 0; v_research integer := 0; v_setups integer := 0; v_candidates integer := 0;
  v_fresh boolean := false; v_release boolean := false; v_mail_ready boolean := false;
  v_items jsonb := '[]'::jsonb; v_item jsonb; r record;
  v_scheduled timestamptz; v_sent timestamptz;
begin
  select * into v_gate from private.stock_api_gate where singleton;
  select * into v_email from private.email_delivery_gate where singleton;
  select * into v_scheduler from private.email_worker_scheduler_gate where singleton;
  select snapshot_id,generated_at,as_of_date into v_snapshot,v_generated,v_date
    from private.stock_research_reference_cache order by generated_at desc,snapshot_id limit 1;
  select count(*),count(*) filter(where payload#>>'{release,internal_research_ready}'='true'),
    count(*) filter(where payload#>>'{setup,candidate_setup}' in ('POCKET_PIVOT','EARLY_BREAKOUT','CONFIRMED_BREAKOUT','RETEST')),
    count(*) filter(where payload#>>'{release,decision_candidate_v7}'='true')
    into v_total,v_research,v_setups,v_candidates
    from private.stock_research_reference_cache where snapshot_id=v_snapshot;
  v_fresh := coalesce(v_generated between now()-interval '96 hours' and now()+interval '5 minutes'
    and v_date between (now() at time zone 'Asia/Ho_Chi_Minh')::date-4 and (now() at time zone 'Asia/Ho_Chi_Minh')::date,false);
  v_release := coalesce(v_gate.api_enabled and v_gate.data_ready and v_gate.data_rights_approved
    and v_gate.compliance_approved and v_gate.active_snapshot_id is not null and v_gate.active_manifest_ref is not null,false);
  v_mail_ready := coalesce(v_email.sending_enabled and v_email.provider_configured and v_email.sender_domain_verified
    and v_email.unsubscribe_ready and v_email.bounce_complaint_ready and v_email.compliance_approved
    and v_scheduler.scheduler_enabled and v_scheduler.scheduler_configured,false);

  if v_release then
    for r in select c.* from private.stock_report_cache c
      where c.snapshot_id=v_gate.active_snapshot_id and c.source_manifest_ref=v_gate.active_manifest_ref
        and c.generated_at <= now() and c.expires_at > now()
        and c.payload->>'data_status'='READY' and c.payload->>'data_grade'='DECISION_GRADE'
        and c.payload->>'data_freshness'='FRESH' and c.payload->>'public_release_allowed'='true'
        and c.payload#>>'{action_contract,schema_version}'='STOCKRADAR_ACTION_V1'
        and c.payload#>>'{action_contract,new_position,state}'='BUY'
      order by c.generated_at desc,c.ticker,c.horizon limit 20
    loop
      select min(o.scheduled_at) filter(where o.status in ('PENDING','PROCESSING')),
        min(o.sent_at) filter(where o.status='SENT') into v_scheduled,v_sent
      from private.stock_signal_events e join private.email_outbox o on o.decision_ref=e.id::text
      where e.ticker=r.ticker and e.horizon=r.horizon and e.source_snapshot_id=r.snapshot_id
        and e.source_manifest_ref=r.source_manifest_ref and e.event_at=r.generated_at
        and e.lane='NEW_POSITION' and e.current_state='BUY' and o.email_kind='EVENT_ALERT'
        and (o.status='SENT' or o.expires_at>now());
      v_item := jsonb_build_object('ticker',r.ticker,'horizon',r.horizon,'action','MUA','publish_status','PUBLISHED',
        'reference_price',r.payload->'current_price',
        'buy_zone',coalesce(nullif(r.payload->'buy_zone','null'::jsonb),jsonb_build_array(r.payload->'buy_zone_low',r.payload->'buy_zone_high')),
        'stop_loss',r.payload->'stop_loss','target',coalesce(nullif(r.payload->'target_near','null'::jsonb),nullif(r.payload->'target_price','null'::jsonb),r.payload->'target_3_6m'),
        'risk_reward',coalesce(nullif(r.payload->'risk_reward','null'::jsonb),r.payload->'risk_reward_to_base'),
        'confirmed_at',r.generated_at,'expires_at',r.expires_at,
        'reasons',case when jsonb_typeof(r.payload#>'{action_contract,new_position,reasons}')='array' then r.payload#>'{action_contract,new_position,reasons}' else '[]'::jsonb end,
        'email_status',case when v_sent is not null then 'SENT' when not v_mail_ready then 'DISABLED' when v_scheduled is not null then 'QUEUED' else 'NOT_QUEUED' end,
        'email_scheduled_at',v_scheduled,'email_sent_at',v_sent);
      v_items := v_items || jsonb_build_array(v_item);
    end loop;
  end if;
  return jsonb_build_object('schema_version','STOCKRADAR_RECOMMENDATION_STATUS_V1','checked_at',now(),
    'data_status',case when jsonb_array_length(v_items)>0 then 'READY' when v_total=0 then 'NO_DATA' when not v_fresh then 'STALE' when v_candidates=0 then 'NO_QUALIFIED_BUYS' else 'PUBLICATION_PENDING' end,
    'items',v_items,'snapshot',jsonb_build_object('snapshot_id',v_snapshot,'evaluated_at',v_generated,'as_of_date',v_date,'fresh',v_fresh),
    'coverage',jsonb_build_object('reviewed',v_total,'research_ready',v_research,'initial_setups',v_setups,'qualified_candidates',v_candidates,'published_buys',jsonb_array_length(v_items)),
    'publication_ready',v_release,
    'schedule',jsonb_build_object('timezone','Asia/Ho_Chi_Minh','basis','WEEKDAY_SCHEDULE_NOT_EXCHANGE_CALENDAR',
      'review_times',jsonb_build_array('08:10','10:30','11:15','13:30','14:15','15:25','16:20'),
      'alert_checkpoints',jsonb_build_array('10:35','11:20','13:35','14:20'),
      'next_review_at',private.stockradar_next_weekday_checkpoint(now(),array['08:10','10:30','11:15','13:30','14:15','15:25','16:20']::time[]),
      'next_daily_planned_at',private.stockradar_next_weekday_checkpoint(now(),array['09:00']::time[])),
    'email',jsonb_build_object('ready',v_mail_ready,'sender_domain_verified',coalesce(v_email.sender_domain_verified,false),
      'status',case when v_mail_ready then 'ENABLED' when not coalesce(v_email.sender_domain_verified,false) then 'DOMAIN_UNVERIFIED' else 'NOT_ENABLED' end,
      'daily_time','09:00','dispatch_interval_minutes',2,'audience','CONSENTED_PREMIUM_WATCHLIST',
      'next_scheduled_at',case when v_mail_ready then (select min(scheduled_at) from private.email_outbox where status='PENDING' and expires_at>now()
        and email_kind in ('DAILY_BRIEF','EVENT_ALERT','POST_SESSION_DIGEST','WEEKLY_REPORT')) else null end));
end;
$$;
revoke all on function public.get_stockradar_recommendation_status_v1() from public;
grant execute on function public.get_stockradar_recommendation_status_v1() to anon,authenticated,service_role;
