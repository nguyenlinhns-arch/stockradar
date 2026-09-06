-- Registration receipts come from actual auth.users INSERTs, never a browser click.
create table private.registration_conversion_receipts (
  event_id uuid primary key default gen_random_uuid(),
  user_id uuid unique references auth.users(id) on delete set null,
  flow_id uuid not null,
  plan_interest text not null check (plan_interest in ('FREE','PREMIUM')),
  created_at timestamptz not null default now(),
  accepted_at timestamptz,
  verified_at timestamptz,
  capi_status text not null default 'CAPI_NOT_CONFIGURED' check (capi_status = 'CAPI_NOT_CONFIGURED')
);
alter table private.registration_conversion_receipts enable row level security;
revoke all on table private.registration_conversion_receipts from public,anon,authenticated;

create function private.capture_registration_receipt()
returns trigger language plpgsql security definer set search_path='' as $$
begin
  if TG_OP='INSERT' and new.raw_user_meta_data->>'signup_source'='stockradar_web_verified_v3'
     and coalesce(new.raw_user_meta_data->>'registration_flow_id','') ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' then
    insert into private.registration_conversion_receipts(user_id,flow_id,plan_interest)
    values(new.id,(new.raw_user_meta_data->>'registration_flow_id')::uuid,
      case when new.raw_user_meta_data->>'selected_plan_interest'='premium' then 'PREMIUM' else 'FREE' end)
    on conflict(user_id) do nothing;
  elsif TG_OP='UPDATE' and old.email_confirmed_at is null and new.email_confirmed_at is not null then
    update private.registration_conversion_receipts set verified_at=new.email_confirmed_at where user_id=new.id;
  end if;
  return new;
end $$;
revoke all on function private.capture_registration_receipt() from public,anon,authenticated;
create trigger stockradar_registration_receipt after insert or update of email_confirmed_at on auth.users
for each row execute function private.capture_registration_receipt();

alter table private.conversion_funnel_events
  add column event_id uuid,
  add column schema_version integer not null default 1,
  add column authority text not null default 'BROWSER' check (authority in ('BROWSER','AUTH_SERVER')),
  add column tier text check (tier in ('GUEST','FREE','PREMIUM')),
  add column horizon text,
  add column model_status text,
  add column first_touch jsonb not null default '{}'::jsonb,
  add column last_touch jsonb not null default '{}'::jsonb;
create unique index conversion_funnel_event_id on private.conversion_funnel_events(event_id) where event_id is not null;
alter table private.conversion_funnel_events drop constraint conversion_funnel_events_event_name_check;
alter table private.conversion_funnel_events add constraint conversion_funnel_events_event_name_check check(event_name in (
  'home_view','ticker_lookup_submit','stock_report_view','premium_preview_view','premium_sample_view','pricing_view',
  'performance_proof_view','signup_view','signup_premium_view','signup_submit','checkout_view','conversion_click',
  'landing_view','ai_question_started','ai_result_success','ai_result_failed','ai_guest_first_result',
  'guest_free_cta_impression','guest_free_cta_click','signup_started','signup_submitted','signup_verification_requested',
  'signup_completed','login_success','return_to_ai_after_registration','premium_view','checkout_started','payment_submitted','premium_activated',
  'free_activation','meaningful_report','meaningful_return_d1','meaningful_return_d7','email_cta_landing'
));

create function private.safe_funnel_touch(p jsonb) returns jsonb
language sql immutable set search_path='' as $$
select coalesce(jsonb_object_agg(key,value),'{}'::jsonb) from jsonb_each_text(coalesce(p,'{}'::jsonb))
where key in ('source','utm_source','utm_medium','utm_campaign','utm_content','utm_term')
and char_length(value) between 1 and 120 and value ~ '^[[:alnum:] _.,+-]+$'
and value !~* '(eyJ|sk-|sb_secret_|Bearer|https?)';
$$;
revoke all on function private.safe_funnel_touch(jsonb) from public,anon,authenticated;

create function public.capture_conversion_event_v2(p_payload jsonb,p_session_hash text,p_ip_hash text)
returns boolean language plpgsql security definer set search_path='' as $$
declare
  v_event text := p_payload->>'event_name';
  v_id uuid := (p_payload->>'event_id')::uuid;
  v_first jsonb := private.safe_funnel_touch(p_payload->'first_touch');
  v_last jsonb := private.safe_funnel_touch(p_payload->'last_touch');
  v_count integer;
begin
  if v_id is null or v_event is null or v_event in ('signup_completed','premium_activated') then raise exception 'invalid browser event'; end if;
  if coalesce(p_payload->>'source_path','') !~ '^/[a-zA-Z0-9_/-]{0,150}$' then raise exception 'invalid source path'; end if;
  if p_session_hash !~ '^[0-9a-f]{64}$' or p_ip_hash !~ '^[0-9a-f]{64}$' then raise exception 'invalid fingerprint'; end if;
  perform pg_advisory_xact_lock(hashtextextended(p_ip_hash,0));
  if (select count(*) from private.conversion_funnel_events where ip_hash=p_ip_hash and occurred_at>now()-interval '1 minute')>=60 then
    raise exception 'rate limit exceeded';
  end if;
  insert into private.conversion_funnel_events(event_id,schema_version,event_name,source_path,ticker,plan_interest,session_hash,ip_hash,tier,horizon,model_status,first_touch,last_touch,utm_source,utm_campaign)
  values(v_id,2,v_event,p_payload->>'source_path',nullif(p_payload->>'ticker',''),p_payload->>'plan_interest',p_session_hash,p_ip_hash,p_payload->>'tier',p_payload->>'horizon',p_payload->>'model_status',v_first,v_last,v_first->>'utm_source',v_first->>'utm_campaign')
  on conflict(event_id) where event_id is not null do nothing;
  get diagnostics v_count=ROW_COUNT;
  return v_count=1;
end $$;
revoke all on function public.capture_conversion_event_v2(jsonb,text,text) from public,anon,authenticated;
grant execute on function public.capture_conversion_event_v2(jsonb,text,text) to service_role;

create function public.finalize_registration_conversion_v1(p_user_id uuid,p_flow_id uuid,p_session_hash text,p_ip_hash text,p_first_touch jsonb,p_last_touch jsonb)
returns jsonb language plpgsql security definer set search_path='' as $$
declare v_row private.registration_conversion_receipts%rowtype;
  v_first jsonb:=private.safe_funnel_touch(p_first_touch); v_last jsonb:=private.safe_funnel_touch(p_last_touch);
begin
  select * into v_row from private.registration_conversion_receipts where user_id=p_user_id and flow_id=p_flow_id
    and created_at between now()-interval '24 hours' and now() for update;
  if not found then return jsonb_build_object('registration_created',false); end if;
  update private.registration_conversion_receipts set accepted_at=coalesce(accepted_at,now()) where event_id=v_row.event_id;
  insert into private.conversion_funnel_events(event_id,schema_version,authority,event_name,source_path,plan_interest,session_hash,ip_hash,tier,first_touch,last_touch,utm_source,utm_campaign)
  values(v_row.event_id,2,'AUTH_SERVER','signup_completed','/signup/',v_row.plan_interest,p_session_hash,p_ip_hash,'FREE',v_first,v_last,v_first->>'utm_source',v_first->>'utm_campaign')
  on conflict(event_id) where event_id is not null do nothing;
  return jsonb_build_object('registration_created',true,'event_id',v_row.event_id);
end $$;
revoke all on function public.finalize_registration_conversion_v1(uuid,uuid,text,text,jsonb,jsonb) from public,anon,authenticated;
grant execute on function public.finalize_registration_conversion_v1(uuid,uuid,text,text,jsonb,jsonb) to service_role;

-- Paid activation is an internal event only, originating in an actual verified grant.
-- This observer never creates a payment, grant or entitlement, and has no Meta mapping.
create function private.capture_premium_activation_v2() returns trigger
language plpgsql security definer set search_path='' as $$
declare v_origin private.conversion_funnel_events%rowtype; v_hash text;
begin
  if new.revoked_at is not null or not exists(select 1 from private.payment_events p
    where p.id=new.payment_event_id and p.status='PAID' and p.verified_at is not null) then return new; end if;
  select e.* into v_origin from private.registration_conversion_receipts r join private.conversion_funnel_events e on e.event_id=r.event_id
    where r.user_id=new.user_id and e.authority='AUTH_SERVER';
  v_hash:=encode(extensions.digest('unattributed-grant:'||new.id::text,'sha256'),'hex');
  insert into private.conversion_funnel_events(event_id,schema_version,authority,event_name,source_path,plan_interest,tier,session_hash,ip_hash,first_touch,last_touch)
  values(new.id,2,'AUTH_SERVER','premium_activated','/thanh-toan/','PREMIUM','PREMIUM',coalesce(v_origin.session_hash,v_hash),coalesce(v_origin.ip_hash,v_hash),coalesce(v_origin.first_touch,'{}'::jsonb),coalesce(v_origin.last_touch,'{}'::jsonb))
  on conflict(event_id) where event_id is not null do nothing;
  return new;
end $$;
revoke all on function private.capture_premium_activation_v2() from public,anon,authenticated;
create trigger stockradar_premium_activation_v2 after insert on private.subscription_grants
for each row execute function private.capture_premium_activation_v2();

-- One row per anonymous session and first-touch campaign. V1 history is not relabelled as V2 evidence.
create view private.free_registration_funnel_sessions_v2 with(security_invoker=true) as
select session_hash,coalesce(first_touch->>'source','direct') source,coalesce(first_touch->>'utm_campaign','(none)') campaign,
  min(occurred_at) filter(where event_name='landing_view') landing_at,
  min(occurred_at) filter(where event_name='ai_question_started') ai_at,
  min(occurred_at) filter(where event_name='ai_result_success') result_at,
  min(occurred_at) filter(where event_name='guest_free_cta_click') cta_at,
  min(occurred_at) filter(where event_name='signup_started') signup_at,
  min(occurred_at) filter(where event_name='signup_completed' and authority='AUTH_SERVER') completed_at,
  count(*) filter(where event_name='ai_question_started') ai_questions,
  count(*) filter(where event_name='ai_result_success') ai_results
from private.conversion_funnel_events where schema_version=2 and occurred_at>=now()-interval '30 days'
group by 1,2,3;
revoke all on private.free_registration_funnel_sessions_v2 from public,anon,authenticated;
create view private.free_registration_funnel_30d_v2 with(security_invoker=true) as
select source,campaign,count(*) filter(where landing_at is not null) landing_views,
  coalesce(sum(ai_questions),0) ai_questions,coalesce(sum(ai_results),0) ai_results,
  count(*) filter(where cta_at is not null) cta_click_sessions,
  count(*) filter(where signup_at is not null) signup_starts,
  count(*) filter(where completed_at is not null) registrations,
  round(100.0*count(*) filter(where ai_at>=landing_at)/nullif(count(*) filter(where landing_at is not null),0),2) landing_to_ai_pct,
  round(100.0*count(*) filter(where cta_at>=result_at)/nullif(count(*) filter(where result_at is not null),0),2) ai_result_to_cta_pct,
  round(100.0*count(*) filter(where signup_at>=cta_at)/nullif(count(*) filter(where cta_at is not null),0),2) cta_to_signup_pct,
  round(100.0*count(*) filter(where completed_at>=signup_at)/nullif(count(*) filter(where signup_at is not null),0),2) signup_to_registration_pct
from private.free_registration_funnel_sessions_v2 group by source,campaign;
revoke all on private.free_registration_funnel_30d_v2 from public,anon,authenticated;
