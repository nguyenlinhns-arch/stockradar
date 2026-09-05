-- Security-definer functions use an empty search_path; qualify pgcrypto explicitly.
create or replace function private.sync_email_scheduler_with_delivery_gate_v1()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_sched private.email_worker_scheduler_gate%rowtype;
  v_secret text;
begin
  if new.sending_enabled is true and old.sending_enabled is distinct from true then
    select * into v_sched
    from private.email_worker_scheduler_gate g
    where g.singleton is true
    for update;

    if v_sched.singleton is null or v_sched.scheduler_configured is not true then
      raise exception 'email worker scheduler must be configured before delivery activation';
    end if;

    select ds.decrypted_secret
      into v_secret
    from vault.decrypted_secrets ds
    where ds.name='stockradar_email_worker_scheduler_token'
    order by ds.created_at desc
    limit 1;

    if length(coalesce(v_secret,'')) < 64
       or encode(extensions.digest(v_secret,'sha256'),'hex') <> v_sched.token_hash then
      raise exception 'email worker scheduler Vault token is missing or invalid';
    end if;

    update private.email_worker_scheduler_gate
       set scheduler_enabled=true,
           evidence_ref='ENABLED_BY_EMAIL_DELIVERY_GATE',
           updated_at=now()
     where singleton is true;
  elsif new.sending_enabled is false and old.sending_enabled is distinct from false then
    update private.email_worker_scheduler_gate
       set scheduler_enabled=false,
           evidence_ref='DISABLED_BY_EMAIL_DELIVERY_GATE',
           updated_at=now()
     where singleton is true;
  end if;

  return new;
end;
$$;

revoke all on function private.sync_email_scheduler_with_delivery_gate_v1() from public,anon,authenticated;


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
     or encode(extensions.digest(v_secret,'sha256'),'hex') <> v_sched.token_hash then
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
