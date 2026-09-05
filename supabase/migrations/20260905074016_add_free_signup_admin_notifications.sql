alter table private.email_outbox
  drop constraint if exists email_outbox_email_kind_check;

alter table private.email_outbox
  add constraint email_outbox_email_kind_check
  check (email_kind = any (array[
    'DAILY_BRIEF'::text,
    'EVENT_ALERT'::text,
    'POST_SESSION_DIGEST'::text,
    'WEEKLY_REPORT'::text,
    'WELCOME_FREE'::text,
    'WELCOME_PREMIUM_PENDING'::text,
    'WELCOME_PREMIUM_ACTIVE'::text,
    'ADMIN_FREE_SIGNUP'::text
  ]));

create or replace function public.claim_stockradar_admin_signup_outbox_v1(p_limit integer default 20)
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
set search_path to ''
as $$
begin
  if p_limit < 1 or p_limit > 100 then
    raise exception 'invalid claim limit';
  end if;

  update private.email_outbox
     set status='FAILED', claim_started_at=null, last_error='CLAIM_TIMEOUT'
   where email_kind='ADMIN_FREE_SIGNUP'
     and status='PROCESSING'
     and claim_started_at < now() - interval '10 minutes'
     and attempts < 4;

  update private.email_outbox
     set status='SUPPRESSED', claim_started_at=null, last_error='EXPIRED_BEFORE_SEND'
   where email_kind='ADMIN_FREE_SIGNUP'
     and status in ('PENDING','FAILED','PROCESSING')
     and expires_at <= now();

  update private.email_outbox
     set status='SUPPRESSED', claim_started_at=null, last_error='MAX_ATTEMPTS'
   where email_kind='ADMIN_FREE_SIGNUP'
     and status='FAILED'
     and attempts >= 4;

  return query
  with candidates as (
    select o.id
      from private.email_outbox o
      join auth.users u on u.id=o.user_id
      cross join lateral (
        select lower(trim(c.approver_email)) as approver_email
          from private.checkout_approval_config c
         where c.singleton is true
           and nullif(trim(c.approver_email),'') is not null
         limit 1
      ) cfg
     where o.email_kind='ADMIN_FREE_SIGNUP'
       and o.status in ('PENDING','FAILED')
       and o.scheduled_at <= now()
       and o.expires_at > now()
       and o.attempts < 4
       and u.email is not null
     order by o.priority asc, o.scheduled_at asc, o.created_at asc
     for update of o skip locked
     limit p_limit
  ), claimed as (
    update private.email_outbox o
       set status='PROCESSING', attempts=attempts+1, claim_started_at=now(), last_error=null
      from candidates c
     where o.id=c.id
     returning o.*
  )
  select c.id,
         c.idempotency_key,
         c.user_id,
         cfg.approver_email,
         c.email_kind,
         c.snapshot_id,
         c.payload,
         c.expires_at,
         c.decision_ref
    from claimed c
    cross join lateral (
      select lower(trim(cc.approver_email)) as approver_email
        from private.checkout_approval_config cc
       where cc.singleton is true
         and nullif(trim(cc.approver_email),'') is not null
       limit 1
    ) cfg;
end;
$$;

revoke all on function public.claim_stockradar_admin_signup_outbox_v1(integer) from public, anon, authenticated;
grant execute on function public.claim_stockradar_admin_signup_outbox_v1(integer) to service_role;

create or replace function public.preflight_stockradar_admin_signup_outbox_v1(p_outbox_id uuid)
returns jsonb
language plpgsql
security definer
set search_path to ''
as $$
declare
  v_row private.email_outbox%rowtype;
  v_admin_email text;
begin
  if p_outbox_id is null then
    raise exception 'outbox_id required';
  end if;

  select * into v_row
    from private.email_outbox o
   where o.id=p_outbox_id
   for update;

  if v_row.id is null then
    return jsonb_build_object('allowed',false,'reason','OUTBOX_NOT_FOUND');
  end if;
  if v_row.email_kind <> 'ADMIN_FREE_SIGNUP' then
    return jsonb_build_object('allowed',false,'reason','INVALID_EMAIL_KIND');
  end if;
  if v_row.status <> 'PROCESSING' then
    return jsonb_build_object('allowed',false,'reason','OUTBOX_NOT_PROCESSING');
  end if;
  if v_row.expires_at <= now() then
    update private.email_outbox
       set status='SUPPRESSED', claim_started_at=null, last_error='EXPIRED_AT_PREFLIGHT'
     where id=v_row.id;
    return jsonb_build_object('allowed',false,'reason','EXPIRED_AT_PREFLIGHT');
  end if;

  select lower(trim(c.approver_email)) into v_admin_email
    from private.checkout_approval_config c
   where c.singleton is true
     and nullif(trim(c.approver_email),'') is not null
   limit 1;

  if v_admin_email is null then
    update private.email_outbox
       set status='FAILED', claim_started_at=null, last_error='ADMIN_EMAIL_NOT_CONFIGURED'
     where id=v_row.id;
    return jsonb_build_object('allowed',false,'reason','ADMIN_EMAIL_NOT_CONFIGURED');
  end if;

  return jsonb_build_object(
    'allowed',true,
    'reason',null,
    'email_kind',v_row.email_kind,
    'expires_at',v_row.expires_at,
    'payload',v_row.payload,
    'attempts',v_row.attempts
  );
end;
$$;

revoke all on function public.preflight_stockradar_admin_signup_outbox_v1(uuid) from public, anon, authenticated;
grant execute on function public.preflight_stockradar_admin_signup_outbox_v1(uuid) to service_role;

create or replace function private.dispatch_stockradar_admin_signup_worker_v1()
returns jsonb
language plpgsql
security definer
set search_path to ''
as $$
declare
  v_sched private.email_worker_scheduler_gate%rowtype;
  v_secret text;
  v_request_id bigint;
  v_due boolean := false;
begin
  select * into v_sched
    from private.email_worker_scheduler_gate g
   where g.singleton is true;

  if v_sched.singleton is null or v_sched.scheduler_configured is not true then
    return jsonb_build_object('status','SCHEDULER_NOT_CONFIGURED');
  end if;
  if v_sched.scheduler_enabled is not true then
    return jsonb_build_object('status','SCHEDULER_DISABLED');
  end if;

  select exists(
    select 1
      from private.email_outbox o
     where o.email_kind='ADMIN_FREE_SIGNUP'
       and o.status in ('PENDING','FAILED')
       and o.scheduled_at <= now()
       and o.expires_at > now()
       and o.attempts < 4
  ) into v_due;

  if v_due is not true then
    return jsonb_build_object('status','NO_DUE_EMAIL');
  end if;

  select ds.decrypted_secret into v_secret
    from vault.decrypted_secrets ds
   where ds.name='stockradar_email_worker_scheduler_token'
   order by ds.created_at desc
   limit 1;

  if length(coalesce(v_secret,'')) < 64
     or encode(extensions.digest(v_secret,'sha256'),'hex') <> v_sched.token_hash then
    return jsonb_build_object('status','SCHEDULER_SECRET_INVALID');
  end if;

  select net.http_post(
    url := v_sched.worker_url,
    headers := jsonb_build_object(
      'Content-Type','application/json',
      'x-stockradar-scheduler',v_secret
    ),
    body := jsonb_build_object('limit',20,'mode','admin-signup'),
    timeout_milliseconds := 8000
  ) into v_request_id;

  return jsonb_build_object('status','DISPATCHED','request_id',v_request_id);
exception when others then
  return jsonb_build_object('status','DISPATCH_FAILED');
end;
$$;

revoke all on function private.dispatch_stockradar_admin_signup_worker_v1() from public, anon, authenticated;

create or replace function private.queue_stockradar_free_signup_admin_notice_v1()
returns trigger
language plpgsql
security definer
set search_path to ''
as $$
declare
  v_selected_plan text;
begin
  if new.email is null then
    return new;
  end if;

  v_selected_plan := lower(coalesce(nullif(trim(new.raw_user_meta_data ->> 'selected_plan_interest'),''),'free'));
  if v_selected_plan='premium' then
    return new;
  end if;

  insert into private.email_outbox(
    idempotency_key,
    user_id,
    email_kind,
    payload,
    status,
    scheduled_at,
    expires_at,
    priority
  ) values (
    'admin-free-signup:' || new.id::text,
    new.id,
    'ADMIN_FREE_SIGNUP',
    jsonb_build_object(
      'template_key','admin_free_signup',
      'transactional',true,
      'new_user_id',new.id,
      'new_user_email',new.email,
      'registered_at',coalesce(new.created_at,now()),
      'email_confirmed',new.email_confirmed_at is not null,
      'account_tier','FREE',
      'selected_plan_interest',v_selected_plan,
      'source','AUTH_SIGNUP'
    ),
    'PENDING',
    now(),
    now()+interval '7 days',
    0
  )
  on conflict (idempotency_key) do nothing;

  perform private.dispatch_stockradar_admin_signup_worker_v1();
  return new;
exception when others then
  return new;
end;
$$;

revoke all on function private.queue_stockradar_free_signup_admin_notice_v1() from public, anon, authenticated;

drop trigger if exists zz_stockradar_queue_free_signup_admin_notice on auth.users;
create trigger zz_stockradar_queue_free_signup_admin_notice
after insert on auth.users
for each row execute function private.queue_stockradar_free_signup_admin_notice_v1();

do $$
begin
  if exists(select 1 from cron.job where jobname='stockradar-admin-signup-email-drain-v1') then
    perform cron.unschedule('stockradar-admin-signup-email-drain-v1');
  end if;
  perform cron.schedule(
    'stockradar-admin-signup-email-drain-v1',
    '*/5 * * * *',
    $cron$select private.dispatch_stockradar_admin_signup_worker_v1();$cron$
  );
end;
$$;
