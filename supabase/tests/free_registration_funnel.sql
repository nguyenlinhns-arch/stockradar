-- Database-owner regression. No test account, email queue or metric survives rollback.
begin;
-- This uncommitted setting affects only this transaction; external sessions keep their configuration.
update private.checkout_approval_config set enabled=false where singleton;
do $$
declare u uuid:=gen_random_uuid(); f uuid:=gen_random_uuid(); e uuid:=gen_random_uuid(); r jsonb; r2 jsonb;
  sh text:=repeat('a',64); ih text:=repeat('b',64); p jsonb; n integer;
  payment uuid:=gen_random_uuid(); grant_id uuid:=gen_random_uuid(); plan_id uuid;
begin
  if has_function_privilege('anon','public.finalize_registration_conversion_v1(uuid,uuid,text,text,jsonb,jsonb)','execute')
    or has_function_privilege('authenticated','public.capture_conversion_event_v2(jsonb,text,text)','execute') then raise exception 'Privileged funnel API exposed'; end if;
  if has_table_privilege('anon','private.registration_conversion_receipts','select') then raise exception 'Receipts exposed'; end if;
  r:=public.finalize_registration_conversion_v1(u,f,sh,ih,'{}','{}');
  if r->>'registration_created'<>'false' then raise exception 'Click without Auth insert converted'; end if;
  insert into auth.users(id,email,raw_user_meta_data) values(u,u::text||'@example.invalid',jsonb_build_object('signup_source','stockradar_web_verified_v3','registration_flow_id',f,'selected_plan_interest','free'));
  r:=public.finalize_registration_conversion_v1(u,gen_random_uuid(),sh,ih,'{}','{}');
  if r->>'registration_created'<>'false' then raise exception 'Existing account/new flow converted'; end if;
  r:=public.finalize_registration_conversion_v1(u,f,sh,ih,'{"source":"facebook","utm_campaign":"free_launch","email":"private@example.invalid"}','{}');
  r2:=public.finalize_registration_conversion_v1(u,f,sh,ih,'{}','{}');
  if r->>'registration_created'<>'true' or r->>'event_id'<>r2->>'event_id' then raise exception 'Receipt not stable'; end if;
  select count(*) into n from private.conversion_funnel_events where event_id=(r->>'event_id')::uuid and authority='AUTH_SERVER' and event_name='signup_completed';
  if n<>1 then raise exception 'Duplicate or missing registration'; end if;
  if (select first_touch::text like '%private%' from private.conversion_funnel_events where event_id=(r->>'event_id')::uuid) then raise exception 'PII stored'; end if;
  update auth.users set email_confirmed_at=now() where id=u;
  if not exists(select 1 from private.registration_conversion_receipts where user_id=u and verified_at is not null) then raise exception 'Verification not observed'; end if;
  p:=jsonb_build_object('event_name','ai_question_started','event_id',e,'source_path','/','tier','GUEST','plan_interest','FREE','first_touch',jsonb_build_object('source','facebook'));
  if not public.capture_conversion_event_v2(p,sh,ih) or public.capture_conversion_event_v2(p,sh,ih) then raise exception 'Browser event dedupe failed'; end if;
  begin
    perform public.capture_conversion_event_v2(p||'{"event_name":"signup_completed"}'::jsonb,sh,ih);
    raise exception 'FAIL browser completion accepted';
  exception when others then if SQLERRM like 'FAIL%' then raise; end if; end;
  begin
    perform public.capture_conversion_event_v2(p||'{"event_name":"premium_activated"}'::jsonb,sh,ih);
    raise exception 'FAIL browser activation accepted';
  exception when others then if SQLERRM like 'FAIL%' then raise; end if; end;
  select id into plan_id from private.billing_plans where plan_code='ADVANCED_TEST';
  insert into private.payment_events(id,provider_name,provider_event_id,user_id,plan_id,amount_vnd,status,occurred_at,verified_at,raw_payload_sha256)
  values(payment,'LOCAL_SQL_FIXTURE',payment::text,u,plan_id,199000,'PAID',now(),now(),repeat('c',64));
  insert into private.subscription_grants(id,user_id,payment_event_id,starts_at,ends_at)
  values(grant_id,u,payment,now(),now()+interval '30 days');
  if (select count(*) from private.conversion_funnel_events where event_id=grant_id and event_name='premium_activated' and authority='AUTH_SERVER')<>1 then raise exception 'Verified grant activation missing'; end if;
end $$;
select 'PASS actual Auth insert receipt; stable dedupe; verification; server-only completion; sanitized attribution' as result;
rollback;
