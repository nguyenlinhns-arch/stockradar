-- Copy the exact report's own horizon targets; never substitute a different horizon.
create or replace function private.stockradar_email_price_plan_v1(p_report jsonb, p_horizon text)
returns jsonb language sql immutable set search_path = '' as $$
  select jsonb_build_object('horizon',p_horizon,
    'stop',p_report->'stop_loss','stop_loss',p_report->'stop_loss',
    'target_near',p_report->'target_near','target_3_6m',p_report->'target_3_6m',
    'target_12m',p_report->'target_12m','target_price',p_report->'target_price',
    'target',case p_horizon when 'MEDIUM_TERM' then p_report->'target_3_6m'
      when 'LONG_TERM' then p_report->'target_12m'
      when 'ACCUMULATION' then p_report->'target_price'
      else coalesce(nullif(p_report->'target_near','null'::jsonb),p_report->'target_price') end);
$$;
revoke all on function private.stockradar_email_price_plan_v1(jsonb,text) from public,anon,authenticated;

CREATE OR REPLACE FUNCTION public.get_stockradar_recommendation_status_v1()
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  v_gate private.stock_api_gate%rowtype;
  v_email private.email_delivery_gate%rowtype;
  v_scheduler private.email_worker_scheduler_gate%rowtype;
  v_snapshot text; v_generated timestamptz; v_date date;
  v_total integer := 0; v_research integer := 0; v_setups integer := 0; v_candidates integer := 0;
  v_fresh boolean := false; v_release boolean := false; v_mail_ready boolean := false;
  v_items jsonb := '[]'::jsonb; v_item jsonb; r record;
  v_scheduled timestamptz; v_sent timestamptz;
  v_email_provider text; v_domain_verified boolean := false;
begin
  select * into v_gate from private.stock_api_gate where singleton;
  select * into v_email from private.email_delivery_gate where singleton;
  select * into v_scheduler from private.email_worker_scheduler_gate where singleton;
  -- Sender verification can finish before product delivery is activated. Read
  -- the latest audited result for the selected provider without enabling mail.
  v_email_provider := coalesce(nullif(upper(trim(v_email.provider_name)),''),
    (select upper(trim(e.provider_name)) from private.email_delivery_approval_events e order by e.recorded_at desc,e.id desc limit 1));
  v_domain_verified := coalesce((select e.granted from private.email_delivery_approval_events e
    where upper(trim(e.provider_name))=v_email_provider and e.approval_type='SENDER_DOMAIN'
    order by e.recorded_at desc,e.id desc limit 1),v_email.sender_domain_verified,false);
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
      v_item := v_item || private.stockradar_email_price_plan_v1(r.payload,r.horizon);
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
    'email',jsonb_build_object('ready',v_mail_ready,'sender_domain_verified',v_domain_verified,
      'status',case when v_mail_ready then 'ENABLED' when not v_domain_verified then 'DOMAIN_UNVERIFIED' else 'NOT_ENABLED' end,
      'daily_time','09:00','dispatch_interval_minutes',2,'audience','CONSENTED_PREMIUM_WATCHLIST',
      'next_scheduled_at',case when v_mail_ready then (select min(scheduled_at) from private.email_outbox where status='PENDING' and expires_at>now()
        and email_kind in ('DAILY_BRIEF','EVENT_ALERT','POST_SESSION_DIGEST','WEEKLY_REPORT')) else null end));
end;
$function$;

CREATE OR REPLACE FUNCTION private.process_stockradar_alert_transitions_v1(p_emit_notifications boolean DEFAULT true, p_enqueue_emails boolean DEFAULT true)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  r record;
  v_lane text;
  v_lane_key text;
  v_lane_payload jsonb;
  v_action_contract jsonb;
  v_next_state text;
  v_setup text;
  v_actionable boolean;
  v_prev_state text;
  v_event_key text;
  v_event_id uuid;
  v_notification_id uuid;
  v_title text;
  v_body text;
  v_email_payload jsonb;
  v_email_id uuid;
  v_reasons jsonb;
  recipient record;
  v_scanned integer := 0;
  v_baselined integer := 0;
  v_transitions integer := 0;
  v_actionable_events integer := 0;
  v_notifications integer := 0;
  v_emails integer := 0;
  v_invalid integer := 0;
begin
  perform pg_advisory_xact_lock(hashtextextended('stockradar-alert-transitions-v1',0));
  for r in
    select c.ticker,c.horizon,c.snapshot_id,c.generated_at,c.expires_at,c.payload,c.source_manifest_ref
      from private.stock_report_cache c
     where c.expires_at > now() and c.generated_at <= now()
       and exists (select 1 from private.stock_api_gate g where g.singleton
         and g.api_enabled and g.data_ready and g.data_rights_approved and g.compliance_approved
         and g.active_snapshot_id=c.snapshot_id and g.active_manifest_ref=c.source_manifest_ref)
       and upper(coalesce(c.payload->>'data_status','')) = 'READY'
       and upper(coalesce(c.payload->>'data_grade','')) = 'DECISION_GRADE'
       and coalesce(c.payload->>'public_release_allowed','false') = 'true'
  loop
    v_scanned := v_scanned + 1;
    v_action_contract := r.payload->'action_contract';

    if jsonb_typeof(v_action_contract) <> 'object'
       or coalesce(v_action_contract->>'schema_version','') <> 'STOCKRADAR_ACTION_V1'
       or coalesce(v_action_contract->>'alert_eligible','false') <> 'true'
       or upper(coalesce(r.payload->>'data_freshness','')) <> 'FRESH' then
      v_invalid := v_invalid + 1;
      continue;
    end if;

    foreach v_lane in array array['NEW_POSITION','HOLDING']
    loop
      v_lane_key := case when v_lane='NEW_POSITION' then 'new_position' else 'holding' end;
      v_lane_payload := v_action_contract->v_lane_key;
      v_next_state := upper(trim(coalesce(v_lane_payload->>'state','')));

      if jsonb_typeof(v_lane_payload) <> 'object'
         or (v_lane='NEW_POSITION' and v_next_state not in ('WAIT','BUY'))
         or (v_lane='HOLDING' and v_next_state not in ('WAIT','HOLD','ADD','REDUCE','SELL')) then
        v_invalid := v_invalid + 1;
        continue;
      end if;

      v_setup := nullif(upper(trim(coalesce(v_lane_payload->>'setup', r.payload->>'setup',''))),'');
      v_actionable := v_next_state in ('BUY','ADD','REDUCE','SELL');
      v_prev_state := null;

      select s.current_state
        into v_prev_state
        from private.stock_signal_state s
       where s.ticker=r.ticker and s.horizon=r.horizon and s.lane=v_lane
       for update;

      if v_prev_state is null then
        insert into private.stock_signal_state(
          ticker,horizon,lane,current_state,setup,source_snapshot_id,source_manifest_ref,
          reference_price,evaluated_at,payload,updated_at
        ) values (
          r.ticker,r.horizon,v_lane,v_next_state,v_setup,r.snapshot_id,r.source_manifest_ref,
          nullif(r.payload->>'current_price','')::numeric,r.generated_at,
          jsonb_build_object('action_contract',v_lane_payload,'report_snapshot_id',r.snapshot_id),now()
        )
        on conflict (ticker,horizon,lane) do update set
          current_state=excluded.current_state,
          setup=excluded.setup,
          source_snapshot_id=excluded.source_snapshot_id,
          source_manifest_ref=excluded.source_manifest_ref,
          reference_price=excluded.reference_price,
          evaluated_at=excluded.evaluated_at,
          payload=excluded.payload,
          updated_at=now();
        v_baselined := v_baselined + 1;
        continue;
      end if;

      if v_prev_state = v_next_state then
        update private.stock_signal_state
           set setup=v_setup,
               source_snapshot_id=r.snapshot_id,
               source_manifest_ref=r.source_manifest_ref,
               reference_price=nullif(r.payload->>'current_price','')::numeric,
               evaluated_at=r.generated_at,
               payload=jsonb_build_object('action_contract',v_lane_payload,'report_snapshot_id',r.snapshot_id),
               updated_at=now()
         where ticker=r.ticker and horizon=r.horizon and lane=v_lane;
        continue;
      end if;

      v_event_key := md5(concat_ws('|',r.ticker,r.horizon,v_lane,v_prev_state,v_next_state,r.snapshot_id));
      v_event_id := null;

      insert into private.stock_signal_events(
        event_key,ticker,horizon,lane,previous_state,current_state,setup,actionable,
        source_snapshot_id,source_manifest_ref,reference_price,event_at,payload
      ) values (
        v_event_key,r.ticker,r.horizon,v_lane,v_prev_state,v_next_state,v_setup,v_actionable,
        r.snapshot_id,r.source_manifest_ref,nullif(r.payload->>'current_price','')::numeric,r.generated_at,
        jsonb_build_object(
          'action_contract',v_lane_payload,
          'report_snapshot_id',r.snapshot_id,
          'reasons',coalesce(v_lane_payload->'reasons','[]'::jsonb)
        )
      )
      on conflict (event_key) do nothing
      returning id into v_event_id;

      update private.stock_signal_state
         set current_state=v_next_state,
             setup=v_setup,
             source_snapshot_id=r.snapshot_id,
             source_manifest_ref=r.source_manifest_ref,
             reference_price=nullif(r.payload->>'current_price','')::numeric,
             evaluated_at=r.generated_at,
             payload=jsonb_build_object('action_contract',v_lane_payload,'report_snapshot_id',r.snapshot_id),
             updated_at=now()
       where ticker=r.ticker and horizon=r.horizon and lane=v_lane;

      v_transitions := v_transitions + 1;
      if v_event_id is null or not v_actionable then
        continue;
      end if;
      v_actionable_events := v_actionable_events + 1;

      if not p_emit_notifications then
        continue;
      end if;

      v_title := case
        when v_next_state='BUY' and v_setup='POCKET_PIVOT' then 'ĐẠT ĐIỂM MUA SỚM'
        when v_next_state='BUY' and v_setup='EARLY_BREAKOUT' then 'ĐẠT ĐIỂM MUA KHI VƯỢT NỀN'
        when v_next_state='BUY' and v_setup='CONFIRMED_BREAKOUT' then 'ĐẠT ĐIỂM MUA – XÁC NHẬN'
        when v_next_state='BUY' then 'ĐẠT ĐIỂM MUA'
        when v_next_state='ADD' then 'MUA THÊM'
        when v_next_state='REDUCE' then 'HẠ TỶ TRỌNG'
        when v_next_state='SELL' then 'CẮT LỖ / BÁN'
        else 'THAY ĐỔI TRẠNG THÁI'
      end;
      v_body := r.ticker || ' · ' || v_prev_state || ' → ' || v_next_state || ' · ' || r.horizon;
      v_reasons := case when jsonb_typeof(v_lane_payload->'reasons')='array' then v_lane_payload->'reasons' else '[]'::jsonb end;

      for recipient in
        select w.user_id,
               e.eligible_for_premium as email_premium,
               e.event_alerts as email_event_alerts
          from public.watchlist_items w
          join public.profiles p on p.id=w.user_id
          left join private.product_email_eligibility e on e.user_id=w.user_id
         where w.ticker=r.ticker
           and w.horizon=r.horizon
           and w.removed_at is null
           and w.alert_enabled
           and p.account_status='ACTIVE'
           and p.account_tier in ('TRIAL','PAID')
           and ((v_lane='HOLDING' and w.owns_stock) or (v_lane='NEW_POSITION' and not w.owns_stock))
      loop
        v_notification_id := null;
        insert into public.stockradar_notifications(
          user_id,event_id,ticker,horizon,lane,previous_state,current_state,title,body,payload,expires_at
        ) values (
          recipient.user_id,v_event_id,r.ticker,r.horizon,v_lane,v_prev_state,v_next_state,
          v_title,v_body,
          jsonb_build_object(
            'schema_version','STOCKRADAR_NOTIFICATION_V1',
            'ticker',r.ticker,
            'horizon',r.horizon,
            'lane',v_lane,
            'previous_state',v_prev_state,
            'current_state',v_next_state,
            'setup',v_setup,
            'reference_price',r.payload->'current_price',
            'snapshot_id',r.snapshot_id
          ),
          r.expires_at
        )
        on conflict (user_id,event_id) do nothing
        returning id into v_notification_id;

        if v_notification_id is not null then
          v_notifications := v_notifications + 1;
        end if;

        if p_enqueue_emails
           and coalesce(recipient.email_premium,false)
           and coalesce(recipient.email_event_alerts,false) then
          v_email_payload := jsonb_build_object(
            'subject','[StockRadar] ' || v_title || ' · ' || r.ticker,
            'preheader',r.ticker || ' vừa chuyển trạng thái ' || v_prev_state || ' → ' || v_next_state,
            'ticker',r.ticker,
            'previous_state',v_prev_state,
            'current_state',v_next_state,
            'reasons',v_reasons,
            'decision_card',jsonb_build_object(
              'ticker',r.ticker,
              'previous_state',v_prev_state,
              'current_state',v_next_state,
              'evaluated_at',r.generated_at,
              'new_position_decision',v_action_contract#>>'{new_position,state}',
              'holding_decision',v_action_contract#>>'{holding,state}',
              'reference_price',r.payload->'current_price',
              'buy_zone',coalesce(r.payload->'buy_zone',jsonb_build_array(r.payload->'buy_zone_low',r.payload->'buy_zone_high')),
              'stop',r.payload->'stop_loss',
              'target',coalesce(r.payload->'target_near',r.payload->'target_price',r.payload->'target_3_6m'),
              'risk_reward',r.payload->'risk_reward',
              'invalidation',r.payload->'invalidation_conditions',
              'next_review',private.stockradar_next_weekday_checkpoint(now(),array['10:30','11:15','13:30','14:15','15:25','16:20']::time[])
            ) || private.stockradar_email_price_plan_v1(r.payload,r.horizon),
            'no_chase_notice',case when v_next_state='BUY' then 'Không mua cao hơn vùng giá mua; luôn kiểm tra trạng thái mới nhất trước khi đặt lệnh.' else null end,
            'late_open_notice','Nếu mở email muộn, hãy xem trạng thái mới nhất trên StockRadar trước khi hành động.'
          );

          v_email_id := public.enqueue_stockradar_email_v2(
            recipient.user_id,
            'EVENT_ALERT',
            'event-v1-' || md5(recipient.user_id::text || '|' || v_event_key),
            r.snapshot_id,
            v_email_payload,
            now(),
            least(r.expires_at, now() + interval '6 hours'),
            90,
            v_event_id::text
          );
          if v_email_id is not null then
            v_emails := v_emails + 1;
          end if;
        end if;
      end loop;
    end loop;
  end loop;

  return jsonb_build_object(
    'ok',true,
    'scanned_reports',v_scanned,
    'baselined_states',v_baselined,
    'transitions',v_transitions,
    'actionable_events',v_actionable_events,
    'notifications_created',v_notifications,
    'emails_enqueued',v_emails,
    'invalid_or_ineligible_contracts',v_invalid
  );
end;
$function$;

CREATE OR REPLACE FUNCTION public.preflight_stockradar_email_outbox_v1(p_outbox_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  v_row private.email_outbox%rowtype;
  v_elig private.product_email_eligibility%rowtype;
  v_verified boolean := false;
  v_allowed boolean := false;
  v_reason text := 'NOT_ELIGIBLE';
  v_render_payload jsonb;
  v_card jsonb;
  v_opportunities jsonb;
begin
  if p_outbox_id is null then raise exception 'outbox_id required'; end if;

  select * into v_row
  from private.email_outbox o
  where o.id = p_outbox_id
  for update;

  if v_row.id is null then
    return jsonb_build_object('allowed',false,'reason','OUTBOX_NOT_FOUND');
  end if;
  if v_row.status <> 'PROCESSING' then
    return jsonb_build_object('allowed',false,'reason','OUTBOX_NOT_PROCESSING');
  end if;
  if v_row.expires_at <= now() then
    update private.email_outbox
       set status='SUPPRESSED',claim_started_at=null,last_error='EXPIRED_AT_PREFLIGHT'
     where id=v_row.id;
    return jsonb_build_object('allowed',false,'reason','EXPIRED_AT_PREFLIGHT');
  end if;

  select (u.email_confirmed_at is not null and u.email is not null)
    into v_verified
  from auth.users u where u.id=v_row.user_id;
  if v_verified is not true then
    update private.email_outbox
       set status='SUPPRESSED',claim_started_at=null,last_error='EMAIL_NOT_VERIFIED_AT_PREFLIGHT'
     where id=v_row.id;
    return jsonb_build_object('allowed',false,'reason','EMAIL_NOT_VERIFIED_AT_PREFLIGHT');
  end if;

  select * into v_elig
  from private.product_email_eligibility e
  where e.user_id=v_row.user_id;

  if v_elig.user_id is null then
    v_reason := 'NO_EMAIL_PREFERENCE_AT_PREFLIGHT';
  elsif v_row.email_kind='DAILY_BRIEF' and v_elig.eligible_to_send and v_elig.daily_brief then
    v_allowed := true;
  elsif v_row.email_kind='EVENT_ALERT' and v_elig.eligible_for_premium and v_elig.event_alerts then
    v_allowed := true;
  elsif v_row.email_kind='POST_SESSION_DIGEST' and v_elig.eligible_for_premium and v_elig.post_session_digest then
    v_allowed := true;
  elsif v_row.email_kind='WEEKLY_REPORT' and v_elig.eligible_for_premium and v_elig.weekly_report then
    v_allowed := true;
  elsif v_elig.suppression_reason is not null then
    v_reason := 'SUPPRESSED_AT_PREFLIGHT_' || v_elig.suppression_reason;
  elsif v_elig.sending_enabled is not true then
    v_reason := 'DELIVERY_DISABLED_AT_PREFLIGHT';
  elsif v_elig.latest_consent_granted is not true then
    v_reason := 'CONSENT_REVOKED_AT_PREFLIGHT';
  else
    v_reason := 'ENTITLEMENT_CHANGED_AT_PREFLIGHT';
  end if;

  -- Re-check approval and the exact report immediately before action content is sent.
  if v_allowed and v_row.email_kind='EVENT_ALERT' then
    v_allowed := exists(select 1 from private.stock_signal_events e
      join private.stock_report_cache c on c.ticker=e.ticker and c.horizon=e.horizon
        and c.snapshot_id=e.source_snapshot_id and c.source_manifest_ref=e.source_manifest_ref
        and c.generated_at=e.event_at and c.generated_at<=now() and c.expires_at>now()
      join private.stock_api_gate g on g.singleton and g.api_enabled and g.data_ready
        and g.data_rights_approved and g.compliance_approved
        and g.active_snapshot_id=c.snapshot_id and g.active_manifest_ref=c.source_manifest_ref
      where e.id::text=v_row.decision_ref and c.payload->>'data_status'='READY'
        and c.payload->>'data_grade'='DECISION_GRADE' and c.payload->>'data_freshness'='FRESH'
        and c.payload->>'public_release_allowed'='true'
        and c.payload#>>'{action_contract,schema_version}'='STOCKRADAR_ACTION_V1'
        and c.payload#>>'{action_contract,alert_eligible}'='true'
        and c.payload#>>array['action_contract',case when e.lane='NEW_POSITION' then 'new_position' else 'holding' end,'state']=e.current_state);
    if not v_allowed then v_reason:='ACTION_REPORT_CHANGED_OR_UNRELEASED'; end if;
  elsif v_allowed and v_row.email_kind='DAILY_BRIEF' and jsonb_typeof(v_row.payload->'opportunities')='array' then
    v_allowed := not exists(select 1 from jsonb_array_elements(v_row.payload->'opportunities') i
      where not exists(select 1 from private.stock_report_cache c
        join private.stock_api_gate g on g.singleton and g.api_enabled and g.data_ready
          and g.data_rights_approved and g.compliance_approved
          and g.active_snapshot_id=c.snapshot_id and g.active_manifest_ref=c.source_manifest_ref
        where c.ticker=i->>'ticker' and c.horizon=i->>'horizon'
          and c.snapshot_id=v_row.payload->>'action_snapshot_id'
          and c.source_manifest_ref=v_row.payload->>'action_manifest_ref'
          and c.generated_at=(i->>'confirmed_at')::timestamptz and c.generated_at<=now() and c.expires_at>now()
          and c.payload->>'data_status'='READY' and c.payload->>'data_grade'='DECISION_GRADE'
          and c.payload->>'data_freshness'='FRESH' and c.payload->>'public_release_allowed'='true'
          and c.payload#>>'{action_contract,schema_version}'='STOCKRADAR_ACTION_V1'
          and c.payload#>>'{action_contract,new_position,state}'='BUY'));
    if not v_allowed then v_reason:='DAILY_REPORT_CHANGED_OR_UNRELEASED'; end if;
  end if;

  if v_allowed is not true then
    update private.email_outbox
       set status='SUPPRESSED',claim_started_at=null,last_error=v_reason
     where id=v_row.id;
    return jsonb_build_object('allowed',false,'reason',v_reason);
  end if;

  -- Stored outbox prices are not authoritative. Re-read the exact checked report.
  v_render_payload := v_row.payload;
  if v_row.email_kind='EVENT_ALERT' then
    select private.stockradar_email_price_plan_v1(c.payload,c.horizon) ||
      jsonb_build_object('reference_price',c.payload->'current_price',
        'buy_zone',coalesce(nullif(c.payload->'buy_zone','null'::jsonb),
          jsonb_build_array(c.payload->'buy_zone_low',c.payload->'buy_zone_high')))
      into v_card
    from private.stock_signal_events e join private.stock_report_cache c
      on c.ticker=e.ticker and c.horizon=e.horizon and c.snapshot_id=e.source_snapshot_id
      and c.source_manifest_ref=e.source_manifest_ref and c.generated_at=e.event_at
    where e.id::text=v_row.decision_ref;
    if v_card is null then raise exception 'EMAIL_REPORT_MISSING_AFTER_PREFLIGHT'; end if;
    v_render_payload := jsonb_set(v_render_payload,'{decision_card}',
      coalesce(nullif(v_render_payload->'decision_card','null'::jsonb),'{}'::jsonb) || v_card,true);
  elsif v_row.email_kind='DAILY_BRIEF' and jsonb_typeof(v_row.payload->'opportunities')='array' then
    select coalesce(jsonb_agg(i || private.stockradar_email_price_plan_v1(c.payload,c.horizon) ||
      jsonb_build_object('reference_price',c.payload->'current_price',
        'buy_zone',coalesce(nullif(c.payload->'buy_zone','null'::jsonb),
          jsonb_build_array(c.payload->'buy_zone_low',c.payload->'buy_zone_high'))) order by n),'[]'::jsonb)
    into v_opportunities
    from jsonb_array_elements(v_row.payload->'opportunities') with ordinality as item(i,n)
    join private.stock_report_cache c on c.ticker=i->>'ticker' and c.horizon=i->>'horizon'
      and c.snapshot_id=v_row.payload->>'action_snapshot_id'
      and c.source_manifest_ref=v_row.payload->>'action_manifest_ref'
      and c.generated_at=(i->>'confirmed_at')::timestamptz;
    v_render_payload := jsonb_set(v_render_payload,'{opportunities}',v_opportunities,true);
  end if;

  return jsonb_build_object(
    'allowed',true,
    'reason',null,
    'email_kind',v_row.email_kind,
    'expires_at',v_row.expires_at,
    'payload',v_render_payload,
    'attempts',v_row.attempts
  );
end;
$function$
;
