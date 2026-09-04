-- StockRadar product-email delivery runtime v2.
-- Provider sending remains fail-closed behind private.email_delivery_gate.
-- This migration adds TTL/idempotent outbox claiming, delivery audit, one-click/product unsubscribe,
-- and bounce/complaint suppression without exposing provider secrets to public clients.

alter table private.email_outbox
  add column if not exists expires_at timestamptz,
  add column if not exists priority smallint not null default 50,
  add column if not exists decision_ref text,
  add column if not exists claim_started_at timestamptz;

update private.email_outbox
set expires_at = coalesce(expires_at, scheduled_at + interval '1 day')
where expires_at is null;

alter table private.email_outbox
  alter column expires_at set not null;

alter table private.email_outbox
  drop constraint if exists email_outbox_priority_check;
alter table private.email_outbox
  add constraint email_outbox_priority_check check (priority between 0 and 100);

create index if not exists email_outbox_claimable_v2
  on private.email_outbox(priority asc, scheduled_at asc, created_at asc)
  where status in ('PENDING','FAILED');

create table if not exists private.email_delivery_events (
  id uuid primary key default gen_random_uuid(),
  provider_name text not null,
  provider_event_id text not null,
  provider_message_id text,
  outbox_id uuid references private.email_outbox(id) on delete set null,
  event_type text not null check (event_type in (
    'email.sent','email.delivered','email.delivery_delayed','email.bounced','email.complained',
    'email.opened','email.clicked','email.failed','email.scheduled','email.suppressed'
  )),
  event_at timestamptz not null,
  payload_digest text not null,
  event_meta jsonb not null default '{}'::jsonb,
  received_at timestamptz not null default now(),
  unique(provider_name, provider_event_id)
);

create index if not exists email_delivery_events_by_message
  on private.email_delivery_events(provider_message_id, event_at desc);
create index if not exists email_delivery_events_by_outbox
  on private.email_delivery_events(outbox_id, event_at desc);

create table if not exists private.email_unsubscribe_tokens (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  scope text not null check (scope in ('DAILY_BRIEF','EVENT_ALERT','POST_SESSION_DIGEST','WEEKLY_REPORT','ALL')),
  token_hash text not null unique,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  used_at timestamptz,
  check (expires_at > created_at)
);

create index if not exists email_unsubscribe_tokens_active
  on private.email_unsubscribe_tokens(user_id, scope, expires_at desc)
  where used_at is null;

alter table private.email_delivery_events enable row level security;
alter table private.email_unsubscribe_tokens enable row level security;
revoke all on private.email_delivery_events from public, anon, authenticated;
revoke all on private.email_unsubscribe_tokens from public, anon, authenticated;

alter table public.product_email_consent_events
  drop constraint if exists product_email_consent_events_source_check;
alter table public.product_email_consent_events
  add constraint product_email_consent_events_source_check
  check (source in ('ACCOUNT_CENTER','SIGNUP','SUPPORT','UNSUBSCRIBE'));

create or replace function public.enqueue_stockradar_email_v2(
  p_user_id uuid,
  p_email_kind text,
  p_idempotency_key text,
  p_snapshot_id text,
  p_payload jsonb,
  p_scheduled_at timestamptz,
  p_expires_at timestamptz,
  p_priority integer default 50,
  p_decision_ref text default null
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_kind text := upper(trim(coalesce(p_email_kind, '')));
  v_status text := 'SUPPRESSED';
  v_reason text := 'NOT_ELIGIBLE';
  v_row_id uuid;
  v_elig private.product_email_eligibility%rowtype;
begin
  if p_user_id is null then raise exception 'user_id required'; end if;
  if v_kind not in ('DAILY_BRIEF','EVENT_ALERT','POST_SESSION_DIGEST','WEEKLY_REPORT') then
    raise exception 'invalid email kind';
  end if;
  if length(trim(coalesce(p_idempotency_key, ''))) not between 8 and 256 then
    raise exception 'invalid idempotency key';
  end if;
  if p_payload is null or jsonb_typeof(p_payload) <> 'object' then
    raise exception 'payload must be object';
  end if;
  if p_scheduled_at is null or p_expires_at is null or p_expires_at <= p_scheduled_at then
    raise exception 'invalid delivery time window';
  end if;
  if p_priority not between 0 and 100 then raise exception 'invalid priority'; end if;

  if v_kind = 'EVENT_ALERT' then
    if coalesce(p_payload->>'previous_state','') = '' or coalesce(p_payload->>'current_state','') = '' then
      raise exception 'event alert requires state transition';
    end if;
    if upper(p_payload->>'previous_state') = upper(p_payload->>'current_state') then
      raise exception 'event alert requires material state change';
    end if;
  end if;

  select * into v_elig
  from private.product_email_eligibility e
  where e.user_id = p_user_id;

  if v_elig.user_id is null then
    v_reason := 'NO_EMAIL_PREFERENCE';
  elsif v_kind = 'DAILY_BRIEF' and v_elig.eligible_to_send and v_elig.daily_brief then
    v_status := 'PENDING'; v_reason := null;
  elsif v_kind = 'EVENT_ALERT' and v_elig.eligible_for_premium and v_elig.event_alerts then
    v_status := 'PENDING'; v_reason := null;
  elsif v_kind = 'POST_SESSION_DIGEST' and v_elig.eligible_for_premium and v_elig.post_session_digest then
    v_status := 'PENDING'; v_reason := null;
  elsif v_kind = 'WEEKLY_REPORT' and v_elig.eligible_for_premium and v_elig.weekly_report then
    v_status := 'PENDING'; v_reason := null;
  elsif v_elig.suppression_reason is not null then
    v_reason := 'SUPPRESSED_' || v_elig.suppression_reason;
  elsif v_elig.sending_enabled is not true then
    v_reason := 'DELIVERY_GATE_CLOSED';
  end if;

  insert into private.email_outbox(
    idempotency_key,user_id,email_kind,snapshot_id,payload,status,scheduled_at,expires_at,
    priority,decision_ref,last_error
  ) values (
    trim(p_idempotency_key),p_user_id,v_kind,nullif(trim(coalesce(p_snapshot_id,'')),''),p_payload,
    v_status,p_scheduled_at,p_expires_at,p_priority,nullif(trim(coalesce(p_decision_ref,'')),''),v_reason
  )
  on conflict (idempotency_key) do update
    set idempotency_key = excluded.idempotency_key
  returning id into v_row_id;

  return v_row_id;
end;
$$;

revoke all on function public.enqueue_stockradar_email_v2(uuid,text,text,text,jsonb,timestamptz,timestamptz,integer,text)
  from public, anon, authenticated;
grant execute on function public.enqueue_stockradar_email_v2(uuid,text,text,text,jsonb,timestamptz,timestamptz,integer,text)
  to service_role;

create or replace function public.claim_stockradar_email_outbox_v1(p_limit integer default 20)
returns table(
  outbox_id uuid,
  idempotency_key text,
  user_id uuid,
  recipient_email text,
  email_kind text,
  snapshot_id text,
  payload jsonb,
  expires_at timestamptz,
  decision_ref text
)
language plpgsql
security definer
set search_path = ''
as $$
begin
  if p_limit < 1 or p_limit > 100 then raise exception 'invalid claim limit'; end if;

  update private.email_outbox
     set status = 'FAILED', claim_started_at = null, last_error = 'CLAIM_TIMEOUT'
   where status = 'PROCESSING'
     and claim_started_at < now() - interval '10 minutes'
     and attempts < 4;

  update private.email_outbox
     set status = 'SUPPRESSED', claim_started_at = null, last_error = 'EXPIRED_BEFORE_SEND'
   where status in ('PENDING','FAILED','PROCESSING')
     and expires_at <= now();

  update private.email_outbox
     set status = 'SUPPRESSED', claim_started_at = null, last_error = 'MAX_ATTEMPTS'
   where status = 'FAILED' and attempts >= 4;

  return query
  with candidates as (
    select o.id
    from private.email_outbox o
    join private.product_email_eligibility e on e.user_id = o.user_id
    join auth.users u on u.id = o.user_id
    where o.status in ('PENDING','FAILED')
      and o.scheduled_at <= now()
      and o.expires_at > now()
      and o.attempts < 4
      and u.email_confirmed_at is not null
      and u.email is not null
      and (
        (o.email_kind = 'DAILY_BRIEF' and e.eligible_to_send and e.daily_brief)
        or (o.email_kind = 'EVENT_ALERT' and e.eligible_for_premium and e.event_alerts)
        or (o.email_kind = 'POST_SESSION_DIGEST' and e.eligible_for_premium and e.post_session_digest)
        or (o.email_kind = 'WEEKLY_REPORT' and e.eligible_for_premium and e.weekly_report)
      )
    order by o.priority asc, o.scheduled_at asc, o.created_at asc
    for update of o skip locked
    limit p_limit
  ), claimed as (
    update private.email_outbox o
       set status = 'PROCESSING', attempts = attempts + 1, claim_started_at = now(), last_error = null
      from candidates c
     where o.id = c.id
    returning o.*
  )
  select c.id, c.idempotency_key, c.user_id, u.email, c.email_kind, c.snapshot_id,
         c.payload, c.expires_at, c.decision_ref
  from claimed c
  join auth.users u on u.id = c.user_id;
end;
$$;

revoke all on function public.claim_stockradar_email_outbox_v1(integer) from public, anon, authenticated;
grant execute on function public.claim_stockradar_email_outbox_v1(integer) to service_role;

create or replace function public.finish_stockradar_email_outbox_v1(
  p_outbox_id uuid,
  p_result text,
  p_provider_message_id text default null,
  p_error text default null
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_result text := upper(trim(coalesce(p_result,'')));
begin
  if v_result not in ('SENT','FAILED','SUPPRESSED') then raise exception 'invalid result'; end if;
  if v_result = 'SENT' and length(trim(coalesce(p_provider_message_id,''))) = 0 then
    raise exception 'provider message id required for SENT';
  end if;

  update private.email_outbox
     set status = v_result,
         provider_message_id = case when v_result = 'SENT' then trim(p_provider_message_id) else provider_message_id end,
         last_error = case when v_result = 'SENT' then null else left(coalesce(p_error,'UNKNOWN'), 1000) end,
         sent_at = case when v_result = 'SENT' then now() else sent_at end,
         claim_started_at = null
   where id = p_outbox_id and status = 'PROCESSING';
end;
$$;

revoke all on function public.finish_stockradar_email_outbox_v1(uuid,text,text,text) from public, anon, authenticated;
grant execute on function public.finish_stockradar_email_outbox_v1(uuid,text,text,text) to service_role;

create or replace function public.issue_stockradar_unsubscribe_token_v1(
  p_user_id uuid,
  p_scope text,
  p_ttl_days integer default 90
)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_scope text := upper(trim(coalesce(p_scope,'')));
  v_token text;
begin
  if p_user_id is null then raise exception 'user required'; end if;
  if v_scope not in ('DAILY_BRIEF','EVENT_ALERT','POST_SESSION_DIGEST','WEEKLY_REPORT','ALL') then
    raise exception 'invalid unsubscribe scope';
  end if;
  if p_ttl_days < 1 or p_ttl_days > 365 then raise exception 'invalid token ttl'; end if;

  v_token := replace(gen_random_uuid()::text,'-','') || replace(gen_random_uuid()::text,'-','');

  update private.email_unsubscribe_tokens
     set used_at = now()
   where user_id = p_user_id and scope = v_scope and used_at is null;

  insert into private.email_unsubscribe_tokens(user_id,scope,token_hash,expires_at)
  values (p_user_id,v_scope,encode(digest(v_token,'sha256'),'hex'),now() + make_interval(days => p_ttl_days));

  return v_token;
end;
$$;

revoke all on function public.issue_stockradar_unsubscribe_token_v1(uuid,text,integer) from public, anon, authenticated;
grant execute on function public.issue_stockradar_unsubscribe_token_v1(uuid,text,integer) to service_role;

create or replace function public.apply_stockradar_unsubscribe_v1(p_token text)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_row private.email_unsubscribe_tokens%rowtype;
  v_enabled boolean;
begin
  if length(trim(coalesce(p_token,''))) <> 64 then
    return jsonb_build_object('status','INVALID_TOKEN');
  end if;

  select * into v_row
  from private.email_unsubscribe_tokens t
  where t.token_hash = encode(digest(trim(p_token),'sha256'),'hex')
    and t.used_at is null
    and t.expires_at > now()
  for update;

  if v_row.id is null then
    return jsonb_build_object('status','INVALID_OR_EXPIRED');
  end if;

  if v_row.scope = 'ALL' then
    update public.product_email_preferences
       set enabled=false,daily_brief=false,event_alerts=false,post_session_digest=false,weekly_report=false,updated_at=now()
     where user_id=v_row.user_id;

    insert into private.email_suppressions(user_id,reason,source_ref,created_at,lifted_at)
    values(v_row.user_id,'UNSUBSCRIBE','ONE_CLICK_ALL',now(),null)
    on conflict (user_id) do update
      set reason='UNSUBSCRIBE',source_ref='ONE_CLICK_ALL',created_at=now(),lifted_at=null;

    insert into public.product_email_consent_events(user_id,granted,document_version,source)
    select v_row.user_id,false,g.current_consent_version,'UNSUBSCRIBE'
    from private.email_delivery_gate g where g.singleton is true;
  else
    update public.product_email_preferences
       set daily_brief = case when v_row.scope='DAILY_BRIEF' then false else daily_brief end,
           event_alerts = case when v_row.scope='EVENT_ALERT' then false else event_alerts end,
           post_session_digest = case when v_row.scope='POST_SESSION_DIGEST' then false else post_session_digest end,
           weekly_report = case when v_row.scope='WEEKLY_REPORT' then false else weekly_report end,
           updated_at=now()
     where user_id=v_row.user_id;

    select (daily_brief or event_alerts or post_session_digest or weekly_report)
      into v_enabled
    from public.product_email_preferences where user_id=v_row.user_id;

    if coalesce(v_enabled,false) is false then
      update public.product_email_preferences set enabled=false,updated_at=now() where user_id=v_row.user_id;
    end if;
  end if;

  update private.email_unsubscribe_tokens set used_at=now() where id=v_row.id;
  return jsonb_build_object('status','UNSUBSCRIBED','scope',v_row.scope);
end;
$$;

revoke all on function public.apply_stockradar_unsubscribe_v1(text) from public, anon, authenticated;
grant execute on function public.apply_stockradar_unsubscribe_v1(text) to service_role;

create or replace function public.record_stockradar_email_delivery_event_v1(
  p_provider_name text,
  p_provider_event_id text,
  p_provider_message_id text,
  p_event_type text,
  p_event_at timestamptz,
  p_payload_digest text,
  p_event_meta jsonb default '{}'::jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_event_type text := lower(trim(coalesce(p_event_type,'')));
  v_outbox_id uuid;
  v_user_id uuid;
  v_reason text;
begin
  if v_event_type not in (
    'email.sent','email.delivered','email.delivery_delayed','email.bounced','email.complained',
    'email.opened','email.clicked','email.failed','email.scheduled','email.suppressed'
  ) then raise exception 'unsupported delivery event'; end if;
  if length(trim(coalesce(p_provider_event_id,''))) = 0 then raise exception 'provider event id required'; end if;
  if p_event_at is null then raise exception 'event_at required'; end if;
  if length(trim(coalesce(p_payload_digest,''))) < 32 then raise exception 'payload digest required'; end if;

  select o.id,o.user_id into v_outbox_id,v_user_id
  from private.email_outbox o
  where o.provider_message_id = nullif(trim(coalesce(p_provider_message_id,'')),'')
  order by o.created_at desc limit 1;

  insert into private.email_delivery_events(
    provider_name,provider_event_id,provider_message_id,outbox_id,event_type,event_at,payload_digest,event_meta
  ) values (
    upper(trim(p_provider_name)),trim(p_provider_event_id),nullif(trim(coalesce(p_provider_message_id,'')),''),
    v_outbox_id,v_event_type,p_event_at,lower(trim(p_payload_digest)),coalesce(p_event_meta,'{}'::jsonb)
  )
  on conflict (provider_name,provider_event_id) do nothing;

  if v_user_id is not null and v_event_type in ('email.bounced','email.complained') then
    v_reason := case when v_event_type='email.complained' then 'COMPLAINT' else 'BOUNCE' end;
    insert into private.email_suppressions(user_id,reason,source_ref,created_at,lifted_at)
    values(v_user_id,v_reason,'PROVIDER_WEBHOOK:'||left(trim(p_provider_event_id),200),now(),null)
    on conflict (user_id) do update
      set reason=excluded.reason,source_ref=excluded.source_ref,created_at=now(),lifted_at=null;
    update public.product_email_preferences set enabled=false,updated_at=now() where user_id=v_user_id;
  end if;

  return jsonb_build_object('status','RECORDED','outbox_id',v_outbox_id);
end;
$$;

revoke all on function public.record_stockradar_email_delivery_event_v1(text,text,text,text,timestamptz,text,jsonb)
  from public, anon, authenticated;
grant execute on function public.record_stockradar_email_delivery_event_v1(text,text,text,text,timestamptz,text,jsonb)
  to service_role;
