-- Validate the active release before processing scheduled transitions; serialize overlapping runs.
create or replace function private.process_stockradar_alert_transitions_v1(
  p_emit_notifications boolean default true,
  p_enqueue_emails boolean default true
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
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
            ),
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
$$;

revoke all on function private.process_stockradar_alert_transitions_v1(boolean,boolean) from public, anon, authenticated;
grant execute on function private.process_stockradar_alert_transitions_v1(boolean,boolean) to service_role;
