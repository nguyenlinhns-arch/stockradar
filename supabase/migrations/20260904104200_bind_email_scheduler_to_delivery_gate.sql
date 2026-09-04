-- Couple the internal worker scheduler to the audited product-email delivery gate.
-- Enabling sending is impossible unless the Vault-backed scheduler is configured and its token matches.
-- Disabling delivery automatically disables scheduler dispatch.

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
       or encode(digest(v_secret,'sha256'),'hex') <> v_sched.token_hash then
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

drop trigger if exists email_delivery_gate_sync_scheduler_v1 on private.email_delivery_gate;
create trigger email_delivery_gate_sync_scheduler_v1
before update of sending_enabled on private.email_delivery_gate
for each row execute function private.sync_email_scheduler_with_delivery_gate_v1();
