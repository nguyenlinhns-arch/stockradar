alter table private.billing_gate
  drop constraint if exists billing_gate_safe_enable;

alter table private.billing_gate
  add constraint billing_gate_safe_enable check (
    not checkout_enabled or (
      provider_configured
      and reconciliation_ready
      and refund_chargeback_ready
      and tax_compliance_approved
      and length(trim(coalesce(provider_name, ''))) > 0
      and length(trim(coalesce(evidence_ref, ''))) > 0
      and (
        webhook_signature_verified
        or upper(trim(provider_name)) = 'MANUAL_VIETQR'
      )
    )
  );

create table if not exists private.manual_checkout_config (
  singleton boolean primary key default true check (singleton),
  bank_bin text,
  bank_name text,
  account_number text,
  account_name text,
  transfer_note_prefix text not null default 'SR',
  enabled boolean not null default false,
  updated_at timestamptz not null default now(),
  constraint manual_checkout_config_safe_enable check (
    not enabled or (
      bank_bin ~ '^[0-9]{6}$'
      and length(trim(coalesce(bank_name, ''))) >= 2
      and account_number ~ '^[0-9]{6,24}$'
      and length(trim(coalesce(account_name, ''))) >= 3
      and transfer_note_prefix ~ '^[A-Z0-9]{2,8}$'
    )
  )
);

insert into private.manual_checkout_config (singleton)
values (true)
on conflict (singleton) do nothing;

alter table private.manual_checkout_config enable row level security;
revoke all on table private.manual_checkout_config from public, anon, authenticated;

create table if not exists private.checkout_requests (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  plan_id uuid not null references private.billing_plans(id) on delete restrict,
  amount_vnd integer not null check (amount_vnd > 0),
  payment_reference text not null unique check (payment_reference ~ '^SR[0-9A-Z]{8,24}$'),
  status text not null default 'PENDING' check (status in ('PENDING','USER_CONFIRMED','PAID','EXPIRED','CANCELLED')),
  expires_at timestamptz not null default (now() + interval '30 minutes'),
  confirmed_at timestamptz,
  paid_at timestamptz,
  provider_event_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint checkout_request_confirmation_consistency check (
    (status <> 'USER_CONFIRMED' or confirmed_at is not null)
    and (status <> 'PAID' or paid_at is not null)
  )
);

create index if not exists checkout_requests_user_created_idx
  on private.checkout_requests(user_id, created_at desc);
create index if not exists checkout_requests_status_expiry_idx
  on private.checkout_requests(status, expires_at);

alter table private.checkout_requests enable row level security;
revoke all on table private.checkout_requests from public, anon, authenticated;

insert into private.billing_plans (plan_code, price_vnd, duration_days, active)
values ('ADVANCED_TEST', 199000, 30, true)
on conflict (plan_code) do update set
  price_vnd = excluded.price_vnd,
  duration_days = excluded.duration_days,
  active = true,
  updated_at = now();

insert into private.billing_plans (plan_code, price_vnd, duration_days, active)
values ('ADVANCED_STANDARD', 299000, 30, false)
on conflict (plan_code) do update set
  price_vnd = excluded.price_vnd,
  duration_days = excluded.duration_days,
  updated_at = now();

create or replace function public.create_my_checkout_request(
  p_plan_code text default 'ADVANCED_TEST'
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  uid uuid := auth.uid();
  plan_row private.billing_plans%rowtype;
  gate_row private.billing_gate%rowtype;
  config_row private.manual_checkout_config%rowtype;
  request_row private.checkout_requests%rowtype;
  reference_value text;
  paid_until_value timestamptz;
begin
  if uid is null then
    raise exception 'AUTH_REQUIRED';
  end if;

  if not exists (
    select 1 from auth.users u
    where u.id = uid and u.email_confirmed_at is not null
  ) then
    raise exception 'EMAIL_VERIFICATION_REQUIRED';
  end if;

  if not exists (
    select 1 from public.profiles p
    where p.id = uid and p.account_status = 'ACTIVE'
  ) then
    raise exception 'ACCOUNT_NOT_ACTIVE';
  end if;

  select * into gate_row
  from private.billing_gate
  where singleton is true;

  select * into config_row
  from private.manual_checkout_config
  where singleton is true;

  if gate_row.checkout_enabled is not true
     or upper(coalesce(gate_row.provider_name, '')) <> 'MANUAL_VIETQR'
     or config_row.enabled is not true then
    raise exception 'CHECKOUT_DISABLED';
  end if;

  select * into plan_row
  from private.billing_plans
  where plan_code = upper(trim(coalesce(p_plan_code, '')))
    and active is true;

  if plan_row.id is null then
    raise exception 'PLAN_NOT_AVAILABLE';
  end if;

  update private.checkout_requests
  set status = 'EXPIRED', updated_at = now()
  where user_id = uid
    and status in ('PENDING','USER_CONFIRMED')
    and expires_at <= now();

  select * into request_row
  from private.checkout_requests
  where user_id = uid
    and plan_id = plan_row.id
    and status in ('PENDING','USER_CONFIRMED')
    and expires_at > now()
  order by created_at desc
  limit 1;

  if request_row.id is null then
    loop
      reference_value := 'SR' || to_char(now(), 'YYMMDD') || upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 8));
      exit when not exists (
        select 1 from private.checkout_requests r where r.payment_reference = reference_value
      );
    end loop;

    insert into private.checkout_requests (
      user_id, plan_id, amount_vnd, payment_reference, status, expires_at
    ) values (
      uid, plan_row.id, plan_row.price_vnd, reference_value, 'PENDING', now() + interval '30 minutes'
    )
    returning * into request_row;
  end if;

  select e.paid_until into paid_until_value
  from private.current_paid_entitlements e
  where e.user_id = uid;

  return jsonb_build_object(
    'checkout_enabled', true,
    'request_id', request_row.id,
    'status', request_row.status,
    'amount_vnd', request_row.amount_vnd,
    'duration_days', plan_row.duration_days,
    'plan_code', plan_row.plan_code,
    'payment_reference', request_row.payment_reference,
    'expires_at', request_row.expires_at,
    'bank_bin', config_row.bank_bin,
    'bank_name', config_row.bank_name,
    'account_number', config_row.account_number,
    'account_name', config_row.account_name,
    'paid_until', paid_until_value
  );
end;
$$;

revoke all on function public.create_my_checkout_request(text) from public, anon;
grant execute on function public.create_my_checkout_request(text) to authenticated;

create or replace function public.confirm_my_checkout_request(p_checkout_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  uid uuid := auth.uid();
  request_row private.checkout_requests%rowtype;
begin
  if uid is null then
    raise exception 'AUTH_REQUIRED';
  end if;

  update private.checkout_requests
  set status = 'USER_CONFIRMED', confirmed_at = coalesce(confirmed_at, now()), updated_at = now()
  where id = p_checkout_id
    and user_id = uid
    and status = 'PENDING'
    and expires_at > now()
  returning * into request_row;

  if request_row.id is null then
    select * into request_row
    from private.checkout_requests
    where id = p_checkout_id and user_id = uid;

    if request_row.id is null then
      raise exception 'CHECKOUT_NOT_FOUND';
    end if;
    if request_row.expires_at <= now() and request_row.status <> 'PAID' then
      update private.checkout_requests
      set status = 'EXPIRED', updated_at = now()
      where id = request_row.id and status <> 'PAID';
      raise exception 'CHECKOUT_EXPIRED';
    end if;
    if request_row.status not in ('USER_CONFIRMED','PAID') then
      raise exception 'CHECKOUT_NOT_CONFIRMABLE';
    end if;
  end if;

  return jsonb_build_object(
    'request_id', request_row.id,
    'status', request_row.status,
    'confirmed_at', request_row.confirmed_at,
    'paid_at', request_row.paid_at
  );
end;
$$;

revoke all on function public.confirm_my_checkout_request(uuid) from public, anon;
grant execute on function public.confirm_my_checkout_request(uuid) to authenticated;

create or replace function public.get_my_checkout_request(p_checkout_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  uid uuid := auth.uid();
  request_row private.checkout_requests%rowtype;
  paid_until_value timestamptz;
begin
  if uid is null then
    raise exception 'AUTH_REQUIRED';
  end if;

  select * into request_row
  from private.checkout_requests
  where id = p_checkout_id and user_id = uid;

  if request_row.id is null then
    raise exception 'CHECKOUT_NOT_FOUND';
  end if;

  if request_row.expires_at <= now() and request_row.status in ('PENDING','USER_CONFIRMED') then
    update private.checkout_requests
    set status = 'EXPIRED', updated_at = now()
    where id = request_row.id;
    request_row.status := 'EXPIRED';
  end if;

  select e.paid_until into paid_until_value
  from private.current_paid_entitlements e
  where e.user_id = uid;

  return jsonb_build_object(
    'request_id', request_row.id,
    'status', request_row.status,
    'amount_vnd', request_row.amount_vnd,
    'payment_reference', request_row.payment_reference,
    'expires_at', request_row.expires_at,
    'confirmed_at', request_row.confirmed_at,
    'paid_at', request_row.paid_at,
    'paid_until', paid_until_value
  );
end;
$$;

revoke all on function public.get_my_checkout_request(uuid) from public, anon;
grant execute on function public.get_my_checkout_request(uuid) to authenticated;

create or replace function private.verify_manual_checkout(
  p_checkout_id uuid,
  p_evidence_ref text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  request_row private.checkout_requests%rowtype;
  plan_row private.billing_plans%rowtype;
  payment_row private.payment_events%rowtype;
  grant_row private.subscription_grants%rowtype;
  start_value timestamptz;
  end_value timestamptz;
  evidence_value text := nullif(trim(coalesce(p_evidence_ref, '')), '');
begin
  if evidence_value is null then
    raise exception 'EVIDENCE_REQUIRED';
  end if;

  select * into request_row
  from private.checkout_requests
  where id = p_checkout_id
  for update;

  if request_row.id is null then
    raise exception 'CHECKOUT_NOT_FOUND';
  end if;

  if request_row.status = 'PAID' then
    select * into payment_row
    from private.payment_events
    where provider_name = 'MANUAL_VIETQR'
      and provider_event_id = 'manual-vietqr:' || request_row.id::text;

    select * into grant_row
    from private.subscription_grants
    where payment_event_id = payment_row.id;

    return jsonb_build_object(
      'status', 'PAID',
      'payment_event_id', payment_row.id,
      'paid_until', grant_row.ends_at,
      'idempotent', true
    );
  end if;

  if request_row.status <> 'USER_CONFIRMED' then
    raise exception 'USER_CONFIRMATION_REQUIRED';
  end if;

  select * into plan_row
  from private.billing_plans
  where id = request_row.plan_id and active is true;

  if plan_row.id is null or plan_row.price_vnd <> request_row.amount_vnd then
    raise exception 'PLAN_MISMATCH';
  end if;

  select greatest(
    now(),
    coalesce(max(g.ends_at), now())
  ) into start_value
  from private.subscription_grants g
  join private.payment_events p on p.id = g.payment_event_id
  where g.user_id = request_row.user_id
    and g.revoked_at is null
    and p.status = 'PAID'
    and p.verified_at is not null
    and g.ends_at > now();

  end_value := start_value + make_interval(days => plan_row.duration_days);

  insert into private.payment_events (
    provider_name,
    provider_event_id,
    user_id,
    plan_id,
    amount_vnd,
    status,
    occurred_at,
    verified_at,
    raw_payload_sha256
  ) values (
    'MANUAL_VIETQR',
    'manual-vietqr:' || request_row.id::text,
    request_row.user_id,
    request_row.plan_id,
    request_row.amount_vnd,
    'PAID',
    coalesce(request_row.confirmed_at, now()),
    now(),
    encode(digest(convert_to(request_row.id::text || ':' || evidence_value, 'UTF8'), 'sha256'), 'hex')
  )
  returning * into payment_row;

  insert into private.subscription_grants (
    user_id,
    payment_event_id,
    starts_at,
    ends_at,
    granted_days
  ) values (
    request_row.user_id,
    payment_row.id,
    start_value,
    end_value,
    plan_row.duration_days
  )
  returning * into grant_row;

  update private.checkout_requests
  set status = 'PAID',
      paid_at = now(),
      provider_event_id = payment_row.provider_event_id,
      updated_at = now()
  where id = request_row.id;

  update public.profiles
  set account_tier = 'PAID',
      account_status = 'ACTIVE',
      updated_at = now()
  where id = request_row.user_id;

  update public.product_email_preferences pref
  set enabled = true, updated_at = now()
  where pref.user_id = request_row.user_id
    and (pref.daily_brief or pref.event_alerts or pref.post_session_digest or pref.weekly_report)
    and exists (
      select 1
      from public.product_email_consent_events ce
      cross join private.email_delivery_gate eg
      where ce.user_id = request_row.user_id
        and ce.granted is true
        and ce.document_version = eg.current_consent_version
        and ce.id = (
          select latest.id
          from public.product_email_consent_events latest
          where latest.user_id = request_row.user_id
          order by latest.recorded_at desc, latest.id desc
          limit 1
        )
    );

  return jsonb_build_object(
    'status', 'PAID',
    'payment_event_id', payment_row.id,
    'grant_id', grant_row.id,
    'starts_at', grant_row.starts_at,
    'paid_until', grant_row.ends_at,
    'granted_days', grant_row.granted_days,
    'idempotent', false
  );
end;
$$;

revoke all on function private.verify_manual_checkout(uuid, text) from public, anon, authenticated;
grant execute on function private.verify_manual_checkout(uuid, text) to service_role;

create or replace function private.sync_stockradar_paid_entitlements()
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  changed_count integer := 0;
  step_count integer := 0;
begin
  update public.profiles p
  set account_tier = 'PAID', updated_at = now()
  where p.account_status = 'ACTIVE'
    and p.account_tier <> 'PAID'
    and exists (
      select 1
      from private.current_paid_entitlements e
      where e.user_id = p.id
    );
  get diagnostics step_count = row_count;
  changed_count := changed_count + step_count;

  update public.profiles p
  set account_tier = 'FREE', updated_at = now()
  where p.account_tier = 'PAID'
    and not exists (
      select 1
      from private.current_paid_entitlements e
      where e.user_id = p.id
    );
  get diagnostics step_count = row_count;
  changed_count := changed_count + step_count;

  return changed_count;
end;
$$;

revoke all on function private.sync_stockradar_paid_entitlements() from public, anon, authenticated;
grant execute on function private.sync_stockradar_paid_entitlements() to service_role;

do $$
declare
  existing_job bigint;
begin
  select jobid into existing_job
  from cron.job
  where jobname = 'stockradar-sync-paid-entitlements'
  limit 1;

  if existing_job is not null then
    perform cron.unschedule(existing_job);
  end if;

  perform cron.schedule(
    'stockradar-sync-paid-entitlements',
    '17 * * * *',
    'select private.sync_stockradar_paid_entitlements();'
  );
end;
$$;
