-- Audited activation path for StockRadar product-email delivery.
-- Service-role may record evidence and call activation/deactivation RPCs, but direct gate mutation is revoked.

create table if not exists private.email_delivery_approval_events (
  id uuid primary key default gen_random_uuid(),
  approval_type text not null check (approval_type in (
    'PROVIDER_CONFIG','SENDER_DOMAIN','UNSUBSCRIBE','BOUNCE_COMPLAINT','COMPLIANCE'
  )),
  provider_name text not null check (length(trim(provider_name)) between 1 and 80),
  granted boolean not null,
  evidence_ref text not null check (length(trim(evidence_ref)) between 1 and 500),
  recorded_at timestamptz not null default now()
);

create index if not exists email_delivery_approval_latest
  on private.email_delivery_approval_events(provider_name, approval_type, recorded_at desc, id desc);

create table if not exists private.email_delivery_activation_events (
  id uuid primary key default gen_random_uuid(),
  action text not null check (action in ('ENABLE','DISABLE','AUTO_DISABLE')),
  provider_name text,
  evidence_ref text not null check (length(trim(evidence_ref)) between 1 and 500),
  approval_snapshot jsonb not null default '{}'::jsonb,
  recorded_at timestamptz not null default now()
);

alter table private.email_delivery_approval_events enable row level security;
alter table private.email_delivery_activation_events enable row level security;
revoke all on private.email_delivery_approval_events from public, anon, authenticated;
revoke all on private.email_delivery_activation_events from public, anon, authenticated;
revoke insert, update, delete on private.email_delivery_gate from service_role;

create or replace function public.record_stockradar_email_delivery_approval_v1(
  p_approval_type text,
  p_provider_name text,
  p_granted boolean,
  p_evidence_ref text
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_type text := upper(trim(coalesce(p_approval_type, '')));
  v_provider text := upper(trim(coalesce(p_provider_name, '')));
  v_evidence text := trim(coalesce(p_evidence_ref, ''));
  v_id uuid;
begin
  if v_type not in ('PROVIDER_CONFIG','SENDER_DOMAIN','UNSUBSCRIBE','BOUNCE_COMPLAINT','COMPLIANCE') then
    raise exception 'invalid email approval type';
  end if;
  if length(v_provider) not between 1 and 80 then raise exception 'provider name required'; end if;
  if length(v_evidence) not between 1 and 500 then raise exception 'evidence_ref required'; end if;

  insert into private.email_delivery_approval_events(approval_type,provider_name,granted,evidence_ref)
  values(v_type,v_provider,p_granted,v_evidence)
  returning id into v_id;

  return v_id;
end;
$$;

create or replace function public.activate_stockradar_email_delivery_v1(
  p_provider_name text,
  p_evidence_ref text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_provider text := upper(trim(coalesce(p_provider_name, '')));
  v_evidence text := trim(coalesce(p_evidence_ref, ''));
  v_provider_ok boolean;
  v_domain_ok boolean;
  v_unsub_ok boolean;
  v_bounce_ok boolean;
  v_compliance_ok boolean;
  v_consent_version text;
  v_snapshot jsonb;
begin
  if length(v_provider) not between 1 and 80 then raise exception 'provider name required'; end if;
  if length(v_evidence) not between 1 and 500 then raise exception 'activation evidence_ref required'; end if;

  perform pg_advisory_xact_lock(hashtextextended('stockradar-email-delivery-activation',0));

  select e.granted into v_provider_ok from private.email_delivery_approval_events e where e.provider_name=v_provider and e.approval_type='PROVIDER_CONFIG' order by e.recorded_at desc,e.id desc limit 1;
  select e.granted into v_domain_ok from private.email_delivery_approval_events e where e.provider_name=v_provider and e.approval_type='SENDER_DOMAIN' order by e.recorded_at desc,e.id desc limit 1;
  select e.granted into v_unsub_ok from private.email_delivery_approval_events e where e.provider_name=v_provider and e.approval_type='UNSUBSCRIBE' order by e.recorded_at desc,e.id desc limit 1;
  select e.granted into v_bounce_ok from private.email_delivery_approval_events e where e.provider_name=v_provider and e.approval_type='BOUNCE_COMPLAINT' order by e.recorded_at desc,e.id desc limit 1;
  select e.granted into v_compliance_ok from private.email_delivery_approval_events e where e.provider_name=v_provider and e.approval_type='COMPLIANCE' order by e.recorded_at desc,e.id desc limit 1;

  if v_provider_ok is not true then raise exception 'current PROVIDER_CONFIG approval required'; end if;
  if v_domain_ok is not true then raise exception 'current SENDER_DOMAIN approval required'; end if;
  if v_unsub_ok is not true then raise exception 'current UNSUBSCRIBE approval required'; end if;
  if v_bounce_ok is not true then raise exception 'current BOUNCE_COMPLAINT approval required'; end if;
  if v_compliance_ok is not true then raise exception 'current COMPLIANCE approval required'; end if;

  select g.current_consent_version into v_consent_version
  from private.email_delivery_gate g where g.singleton is true for update;
  if length(trim(coalesce(v_consent_version,''))) = 0 then raise exception 'current consent version required'; end if;

  v_snapshot := jsonb_build_object(
    'provider_config',v_provider_ok,'sender_domain',v_domain_ok,'unsubscribe',v_unsub_ok,
    'bounce_complaint',v_bounce_ok,'compliance',v_compliance_ok,'consent_version',v_consent_version
  );

  update private.email_delivery_gate
     set provider_name=v_provider,
         provider_configured=true,
         sender_domain_verified=true,
         unsubscribe_ready=true,
         bounce_complaint_ready=true,
         compliance_approved=true,
         evidence_ref=v_evidence,
         sending_enabled=true,
         updated_at=now()
   where singleton is true;

  insert into private.email_delivery_activation_events(action,provider_name,evidence_ref,approval_snapshot)
  values('ENABLE',v_provider,v_evidence,v_snapshot);

  return jsonb_build_object('sending_enabled',true,'provider_name',v_provider,'approval_snapshot',v_snapshot);
end;
$$;

create or replace function public.deactivate_stockradar_email_delivery_v1(p_evidence_ref text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_evidence text := trim(coalesce(p_evidence_ref,''));
  v_provider text;
  v_snapshot jsonb;
begin
  if length(v_evidence) not between 1 and 500 then raise exception 'deactivation evidence_ref required'; end if;
  perform pg_advisory_xact_lock(hashtextextended('stockradar-email-delivery-activation',0));
  select provider_name,jsonb_build_object(
    'provider_configured',provider_configured,'sender_domain_verified',sender_domain_verified,
    'unsubscribe_ready',unsubscribe_ready,'bounce_complaint_ready',bounce_complaint_ready,
    'compliance_approved',compliance_approved,'consent_version',current_consent_version
  ) into v_provider,v_snapshot
  from private.email_delivery_gate where singleton is true for update;

  update private.email_delivery_gate set sending_enabled=false,updated_at=now() where singleton is true;
  insert into private.email_delivery_activation_events(action,provider_name,evidence_ref,approval_snapshot)
  values('DISABLE',v_provider,v_evidence,coalesce(v_snapshot,'{}'::jsonb));
end;
$$;

create or replace function private.auto_disable_email_delivery_on_approval_revoke_v1()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_enabled boolean;
  v_provider text;
begin
  if new.granted is true then return new; end if;
  perform pg_advisory_xact_lock(hashtextextended('stockradar-email-delivery-activation',0));
  select sending_enabled,provider_name into v_enabled,v_provider
  from private.email_delivery_gate where singleton is true for update;
  if v_enabled is true and upper(coalesce(v_provider,''))=upper(new.provider_name) then
    update private.email_delivery_gate
       set sending_enabled=false,
           provider_configured=case when new.approval_type='PROVIDER_CONFIG' then false else provider_configured end,
           sender_domain_verified=case when new.approval_type='SENDER_DOMAIN' then false else sender_domain_verified end,
           unsubscribe_ready=case when new.approval_type='UNSUBSCRIBE' then false else unsubscribe_ready end,
           bounce_complaint_ready=case when new.approval_type='BOUNCE_COMPLAINT' then false else bounce_complaint_ready end,
           compliance_approved=case when new.approval_type='COMPLIANCE' then false else compliance_approved end,
           updated_at=now()
     where singleton is true;
    insert into private.email_delivery_activation_events(action,provider_name,evidence_ref,approval_snapshot)
    values('AUTO_DISABLE',new.provider_name,'APPROVAL_REVOKED:'||new.id::text,jsonb_build_object('approval_type',new.approval_type,'approval_event_id',new.id));
  end if;
  return new;
end;
$$;

create trigger email_delivery_approval_revoke_auto_disable_v1
after insert on private.email_delivery_approval_events
for each row execute function private.auto_disable_email_delivery_on_approval_revoke_v1();

revoke all on function public.record_stockradar_email_delivery_approval_v1(text,text,boolean,text) from public,anon,authenticated;
revoke all on function public.activate_stockradar_email_delivery_v1(text,text) from public,anon,authenticated;
revoke all on function public.deactivate_stockradar_email_delivery_v1(text) from public,anon,authenticated;
revoke all on function private.auto_disable_email_delivery_on_approval_revoke_v1() from public,anon,authenticated;
grant execute on function public.record_stockradar_email_delivery_approval_v1(text,text,boolean,text) to service_role;
grant execute on function public.activate_stockradar_email_delivery_v1(text,text) to service_role;
grant execute on function public.deactivate_stockradar_email_delivery_v1(text) to service_role;
