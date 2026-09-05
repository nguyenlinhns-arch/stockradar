-- Owner-only integration tests. Fixtures, simulated approvals and outbox rows
-- are transaction-local and always rolled back; no network dispatcher is called.
begin;
do $$
declare
  v jsonb; p jsonb; uid uuid:=gen_random_uuid(); v_id uuid; v_at timestamptz; v_token text;
begin
  if private.stockradar_next_weekday_checkpoint('2026-09-04T10:00:00Z',array['09:00']::time[]) <> '2026-09-07T02:00:00Z'::timestamptz then raise exception 'Weekend schedule incorrect'; end if;
  if has_function_privilege('anon','public.get_stockradar_email_provider_config_v1()','execute') or
     has_function_privilege('authenticated','public.get_stockradar_email_provider_config_v1()','execute') or
     has_function_privilege('anon','public.verify_stockradar_email_diagnostic_token_v1(text)','execute') or
     has_function_privilege('authenticated','private.enqueue_stockradar_daily_briefs_v1(timestamptz)','execute') then raise exception 'Private email capability exposed'; end if;
  p := jsonb_build_object('data_status','READY','data_grade','DECISION_GRADE','data_freshness','FRESH','public_release_allowed',true,
    'current_price',20000,'buy_zone',jsonb_build_array(19800,20100),'stop_loss',18500,'target_near',24000,'risk_reward',2.5,
    'private_context','PRIVATE_SENTINEL_NOT_FOR_CLIENTS',
    'action_contract',jsonb_build_object('schema_version','STOCKRADAR_ACTION_V1','alert_eligible',true,
      'new_position',jsonb_build_object('state','BUY','reasons',jsonb_build_array('Approved fixture')),'holding',jsonb_build_object('state','HOLD')));
  insert into private.stock_report_cache(ticker,horizon,snapshot_id,source_manifest_ref,generated_at,expires_at,payload)
    values('ZZZ','SHORT_TERM','test-reco-snapshot','test-reco-manifest',now()-interval '1 minute',now()+interval '1 hour',p)
    on conflict(ticker,horizon) do update set snapshot_id=excluded.snapshot_id,source_manifest_ref=excluded.source_manifest_ref,generated_at=excluded.generated_at,expires_at=excluded.expires_at,payload=excluded.payload;
  update private.stock_api_gate set api_enabled=false where singleton;
  v:=public.get_stockradar_recommendation_status_v1();
  if jsonb_array_length(v->'items')<>0 then raise exception 'Closed gate released buy'; end if;
  v:=private.process_stockradar_alert_transitions_v1(false,false);
  if (v->>'scanned_reports')::integer<>0 then raise exception 'Closed gate processed alerts'; end if;
  update private.stock_api_gate set api_enabled=true,data_ready=true,data_rights_approved=true,compliance_approved=true,
    evidence_ref='ROLLBACK_TEST_ONLY',active_manifest_ref='test-reco-manifest',active_snapshot_id='test-reco-snapshot' where singleton;
  v:=public.get_stockradar_recommendation_status_v1();
  if jsonb_array_length(v->'items')<>1 or v#>>'{items,0,ticker}'<>'ZZZ' or v#>>'{items,0,target}'<>'24000' then raise exception 'Approved buy missing'; end if;
  if v::text like '%PRIVATE_SENTINEL%' or v::text like '%user_id%' or v::text like '%recipient_email%' then raise exception 'Private fields leaked'; end if;
  update private.stock_report_cache set source_manifest_ref='wrong-manifest' where ticker='ZZZ' and horizon='SHORT_TERM';
  if jsonb_array_length(public.get_stockradar_recommendation_status_v1()->'items')<>0 then raise exception 'Wrong manifest released'; end if;
  update private.stock_report_cache set source_manifest_ref='test-reco-manifest',generated_at=now()-interval '2 hours',expires_at=now()-interval '1 hour' where ticker='ZZZ' and horizon='SHORT_TERM';
  if jsonb_array_length(public.get_stockradar_recommendation_status_v1()->'items')<>0 then raise exception 'Expired buy released'; end if;
  update private.stock_report_cache set generated_at=now()+interval '1 minute',expires_at=now()+interval '1 hour' where ticker='ZZZ' and horizon='SHORT_TERM';
  if jsonb_array_length(public.get_stockradar_recommendation_status_v1()->'items')<>0 then raise exception 'Future report released'; end if;
  update private.stock_api_gate set api_enabled=false where singleton;
  v:=private.enqueue_stockradar_daily_briefs_v1('2026-09-05T02:00:00Z');
  if v->>'status'<>'OUTSIDE_DAILY_WINDOW' then raise exception 'Saturday bulletin allowed'; end if;
  v_at:=private.stockradar_next_weekday_checkpoint(now(),array['09:00']::time[]);
  update private.email_delivery_gate set sending_enabled=false where singleton;
  v:=private.enqueue_stockradar_daily_briefs_v1(v_at);
  if v->>'status'<>'EMAIL_DISABLED' then raise exception 'Disabled email queued'; end if;
  insert into private.stock_research_reference_cache(ticker,snapshot_id,generated_at,as_of_date,payload,source_ref,price_snapshot_status)
    values('ZZZ','test-reco-reference',now(),(now() at time zone 'Asia/Ho_Chi_Minh')::date,'{}','ROLLBACK_TEST_ONLY','CURRENT')
    on conflict(ticker) do update set snapshot_id=excluded.snapshot_id,generated_at=excluded.generated_at,as_of_date=excluded.as_of_date,payload=excluded.payload;
  insert into auth.users(id,email,email_confirmed_at) values(uid,uid::text||'@example.invalid',now());
  insert into public.profiles(id,account_tier,account_status) values(uid,'PAID','ACTIVE') on conflict(id) do update set account_tier='PAID',account_status='ACTIVE';
  insert into public.product_email_preferences(user_id,enabled,daily_brief,event_alerts,post_session_digest,weekly_report) values(uid,true,true,true,false,false)
    on conflict(user_id) do update set enabled=true,daily_brief=true,event_alerts=true,post_session_digest=false,weekly_report=false;
  insert into public.product_email_consent_events(user_id,granted,document_version,source)
    select uid,true,current_consent_version,'SUPPORT' from private.email_delivery_gate where singleton;
  update private.email_delivery_gate set provider_configured=true,sender_domain_verified=true,unsubscribe_ready=true,bounce_complaint_ready=true,compliance_approved=true,sending_enabled=true where singleton;
  v:=private.enqueue_stockradar_daily_briefs_v1(v_at);
  select id into v_id from private.email_outbox where user_id=uid and email_kind='DAILY_BRIEF';
  if v_id is null then raise exception 'Eligible verified paid user got no bulletin: %',v; end if;
  perform private.enqueue_stockradar_daily_briefs_v1(v_at);
  if (select count(*) from private.email_outbox where user_id=uid and email_kind='DAILY_BRIEF')<>1 then raise exception 'Duplicate daily bulletin'; end if;
  if (select payload->>'headline' from private.email_outbox where id=v_id) not like 'Chưa có mã%' then raise exception 'Invented buy in empty bulletin'; end if;
  update private.email_outbox set status='PROCESSING' where id=v_id;
  v:=public.preflight_stockradar_email_outbox_v1(v_id);
  if v->>'allowed'<>'true' then raise exception 'Valid no-buy bulletin failed preflight'; end if;
  update private.email_outbox set payload=jsonb_set(payload,'{opportunities}','[{"ticker":"ZZZ","horizon":"SHORT_TERM","confirmed_at":"2026-09-04T03:30:00Z"}]') where id=v_id;
  v:=public.preflight_stockradar_email_outbox_v1(v_id);
  if v->>'allowed'<>'false' or v->>'reason'<>'DAILY_REPORT_CHANGED_OR_UNRELEASED' then raise exception 'Unreleased daily buy passed preflight'; end if;
  update private.email_outbox set status='PROCESSING',payload=jsonb_set(payload,'{opportunities}','[]') where id=v_id;
  v_token:=public.issue_stockradar_unsubscribe_token_v1(uid,'DAILY_BRIEF',90);
  if length(v_token)<>64 then raise exception 'Unsubscribe token not issued'; end if;
  v:=public.apply_stockradar_unsubscribe_v1(v_token);
  if v->>'status'<>'UNSUBSCRIBED' or (select daily_brief from public.product_email_preferences where user_id=uid) then raise exception 'Scope unsubscribe failed'; end if;
  v_token:=public.issue_stockradar_unsubscribe_token_v1(uid,'EVENT_ALERT',90);
  v:=public.apply_stockradar_unsubscribe_v1(v_token);
  if v->>'status'<>'UNSUBSCRIBED' or (select enabled from public.product_email_preferences where user_id=uid) then raise exception 'Last product unsubscribe failed'; end if;
  update public.product_email_preferences set enabled=true,daily_brief=true,event_alerts=true where user_id=uid;
  insert into public.product_email_consent_events(user_id,granted,document_version,source,recorded_at)
    select uid,false,current_consent_version,'SUPPORT',now()+interval '1 second' from private.email_delivery_gate where singleton;
  v:=public.preflight_stockradar_email_outbox_v1(v_id);
  if v->>'allowed'<>'false' then raise exception 'Revoked consent passed preflight'; end if;
end $$;
rollback;
select 'PASS: release gates, manifest, expiry, future data, privacy, weekend, paid eligibility, deduplication and consent revocation' as result;
