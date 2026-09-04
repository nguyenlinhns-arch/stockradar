-- Vault-backed StockRadar email worker scheduler.
-- No provider credential is created here. The generated token only authenticates Postgres Cron -> Edge worker.
-- Scheduler stays disabled until the audited email-delivery activation RPC enables it.

create extension if not exists pg_cron with schema pg_catalog;
create extension if not exists pg_net with schema extensions;

create table if not exists private.email_worker_scheduler_gate (
  singleton boolean primary key default true check (singleton is true),
  worker_url text not null check (worker_url ~ '^https://[A-Za-z0-9.-]+/functions/v1/email-worker$'),
  token_hash text not null check (token_hash ~ '^[a-f0-9]{64}$'),
  scheduler_configured boolean not null default true,
  scheduler_enabled boolean not null default false,
  evidence_ref text,
  updated_at timestamptz not null default now()
);

alter table private.email_worker_scheduler_gate enable row level security;
revoke all on private.email_worker_scheduler_gate from public, anon, authenticated;
revoke insert, update, delete on private.email_worker_scheduler_gate from service_role;

do $$
declare
  v_token text;
  v_hash text;
begin
  select ds.decrypted_secret
    into v_token
  from vault.decrypted_secrets ds
  where ds.name = 'stockradar_email_worker_scheduler_token'
  order by ds.created_at desc
  limit 1;

  if length(coalesce(v_token,'')) < 64 then
    v_token := encode(gen_random_bytes(32),'hex');
    perform vault.create_secret(
      v_token,
      'stockradar_email_worker_scheduler_token',
      'Internal Postgres Cron to StockRadar email-worker authentication token'
    );
  end if;

  v_hash := encode(digest(v_token,'sha256'),'hex');

  insert into private.email_worker_scheduler_gate(
    singleton,worker_url,token_hash,scheduler_configured,scheduler_enabled,evidence_ref,updated_at
  ) values (
    true,
    'https://xamviatbxufjlpiwhebb.supabase.co/functions/v1/email-worker',
    v_hash,
    true,
    false,
    'VAULT_TOKEN_GENERATED_IN_DATABASE',
    now()
  )
  on conflict(singleton) do update
    set worker_url=excluded.worker_url,
        token_hash=excluded.token_hash,
        scheduler_configured=true,
        scheduler_enabled=false,
        evidence_ref=excluded.evidence_ref,
        updated_at=now();
end;
$$;

create or replace function public.verify_stockradar_email_scheduler_token_v1(p_token_hash text)
returns boolean
language sql
security definer
set search_path = ''
as $$
  select coalesce((
    select g.scheduler_configured is true
       and g.scheduler_enabled is true
       and g.token_hash = lower(trim(coalesce(p_token_hash,'')))
    from private.email_worker_scheduler_gate g
    where g.singleton is true
  ), false);
$$;

revoke all on function public.verify_stockradar_email_scheduler_token_v1(text) from public, anon, authenticated;
grant execute on function public.verify_stockradar_email_scheduler_token_v1(text) to service_role;

create or replace function private.dispatch_stockradar_email_worker_v1()
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_sched private.email_worker_scheduler_gate%rowtype;
  v_sending boolean := false;
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

  select g.sending_enabled into v_sending
  from private.email_delivery_gate g
  where g.singleton is true;
  if v_sending is not true then
    return jsonb_build_object('status','DELIVERY_GATE_CLOSED');
  end if;

  select exists(
    select 1
    from private.email_outbox o
    where o.status in ('PENDING','FAILED')
      and o.scheduled_at <= now()
      and o.expires_at > now()
      and o.attempts < 4
  ) into v_due;
  if v_due is not true then
    return jsonb_build_object('status','NO_DUE_EMAIL');
  end if;

  select ds.decrypted_secret
    into v_secret
  from vault.decrypted_secrets ds
  where ds.name='stockradar_email_worker_scheduler_token'
  order by ds.created_at desc
  limit 1;

  if length(coalesce(v_secret,'')) < 64
     or encode(digest(v_secret,'sha256'),'hex') <> v_sched.token_hash then
    update private.email_worker_scheduler_gate
       set scheduler_enabled=false,
           scheduler_configured=false,
           evidence_ref='VAULT_SECRET_MISSING_OR_MISMATCH',
           updated_at=now()
     where singleton is true;
    return jsonb_build_object('status','SCHEDULER_SECRET_INVALID');
  end if;

  select net.http_post(
    url := v_sched.worker_url,
    headers := jsonb_build_object(
      'Content-Type','application/json',
      'x-stockradar-scheduler',v_secret
    ),
    body := jsonb_build_object('limit',50),
    timeout_milliseconds := 8000
  ) into v_request_id;

  return jsonb_build_object('status','DISPATCHED','request_id',v_request_id);
end;
$$;

revoke all on function private.dispatch_stockradar_email_worker_v1() from public, anon, authenticated;

-- Every 2 minutes from 09:00 through 18:59 Vietnam time (02:00-11:59 UTC), Monday-Friday.
-- The dispatcher makes no HTTP call unless delivery is enabled AND an email is actually due.
select cron.schedule(
  'stockradar-email-worker-drain-v1',
  '*/2 2-11 * * 1-5',
  'select private.dispatch_stockradar_email_worker_v1();'
);
