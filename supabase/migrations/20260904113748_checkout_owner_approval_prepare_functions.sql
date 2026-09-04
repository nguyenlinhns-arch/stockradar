create or replace function public.verify_stockradar_checkout_hook_v1(p_token_hash text)
returns boolean
language sql
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from private.checkout_approval_config c
    where c.singleton is true
      and c.enabled is true
      and encode(extensions.digest(convert_to(c.hook_token, 'UTF8'), 'sha256'), 'hex') = lower(trim(coalesce(p_token_hash, '')))
  );
$$;

revoke all on function public.verify_stockradar_checkout_hook_v1(text) from public, anon, authenticated;
grant execute on function public.verify_stockradar_checkout_hook_v1(text) to service_role;

create or replace function public.prepare_stockradar_checkout_approval_v1(
  p_checkout_id uuid,
  p_token_hash text,
  p_ttl_minutes integer default 1440
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  request_row private.checkout_requests%rowtype;
  approval_row private.checkout_approvals%rowtype;
  config_row private.checkout_approval_config%rowtype;
  plan_row private.billing_plans%rowtype;
  customer_email text;
  normalized_hash text := lower(trim(coalesce(p_token_hash, '')));
  ttl_minutes integer := greatest(10, least(coalesce(p_ttl_minutes, 1440), 4320));
  should_send boolean := false;
begin
  if normalized_hash !~ '^[a-f0-9]{64}$' then
    raise exception 'INVALID_APPROVAL_TOKEN_HASH';
  end if;

  select * into config_row
  from private.checkout_approval_config
  where singleton is true and enabled is true;

  if config_row.singleton is not true then
    raise exception 'CHECKOUT_APPROVAL_DISABLED';
  end if;

  select * into request_row
  from private.checkout_requests
  where id = p_checkout_id
  for update;

  if request_row.id is null then
    raise exception 'CHECKOUT_NOT_FOUND';
  end if;

  if request_row.status = 'PAID' then
    return jsonb_build_object(
      'checkout_id', request_row.id,
      'status', 'PAID',
      'should_send', false,
      'payment_reference', request_row.payment_reference
    );
  end if;

  if request_row.status <> 'USER_CONFIRMED' then
    raise exception 'USER_CONFIRMATION_REQUIRED';
  end if;

  select * into plan_row from private.billing_plans where id = request_row.plan_id;
  select u.email into customer_email from auth.users u where u.id = request_row.user_id;

  select * into approval_row
  from private.checkout_approvals
  where checkout_id = request_row.id
  for update;

  if approval_row.checkout_id is null then
    insert into private.checkout_approvals (
      checkout_id, user_id, token_hash, status, expires_at, send_attempts
    ) values (
      request_row.id,
      request_row.user_id,
      normalized_hash,
      'PENDING',
      now() + make_interval(mins => ttl_minutes),
      1
    )
    returning * into approval_row;
    should_send := true;
  elsif approval_row.status = 'PENDING' and approval_row.sent_at is null then
    update private.checkout_approvals
    set token_hash = normalized_hash,
        expires_at = now() + make_interval(mins => ttl_minutes),
        send_attempts = send_attempts + 1,
        last_error = null,
        updated_at = now()
    where checkout_id = request_row.id
    returning * into approval_row;
    should_send := true;
  else
    should_send := false;
  end if;

  return jsonb_build_object(
    'checkout_id', request_row.id,
    'user_id', request_row.user_id,
    'customer_email', customer_email,
    'amount_vnd', request_row.amount_vnd,
    'payment_reference', request_row.payment_reference,
    'plan_code', plan_row.plan_code,
    'duration_days', plan_row.duration_days,
    'approval_status', approval_row.status,
    'approval_expires_at', approval_row.expires_at,
    'approver_email', config_row.approver_email,
    'should_send', should_send
  );
end;
$$;

revoke all on function public.prepare_stockradar_checkout_approval_v1(uuid, text, integer) from public, anon, authenticated;
grant execute on function public.prepare_stockradar_checkout_approval_v1(uuid, text, integer) to service_role;

create or replace function public.mark_stockradar_checkout_approval_delivery_v1(
  p_checkout_id uuid,
  p_token_hash text,
  p_sent boolean,
  p_message_id text default null,
  p_error text default null
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  changed integer;
begin
  update private.checkout_approvals
  set sent_at = case when p_sent then coalesce(sent_at, now()) else sent_at end,
      email_message_id = case when p_sent then nullif(trim(coalesce(p_message_id, '')), '') else email_message_id end,
      last_error = case when p_sent then null else left(coalesce(p_error, 'SEND_FAILED'), 500) end,
      updated_at = now()
  where checkout_id = p_checkout_id
    and token_hash = lower(trim(coalesce(p_token_hash, '')))
    and status = 'PENDING';
  get diagnostics changed = row_count;
  return changed = 1;
end;
$$;

revoke all on function public.mark_stockradar_checkout_approval_delivery_v1(uuid, text, boolean, text, text) from public, anon, authenticated;
grant execute on function public.mark_stockradar_checkout_approval_delivery_v1(uuid, text, boolean, text, text) to service_role;
