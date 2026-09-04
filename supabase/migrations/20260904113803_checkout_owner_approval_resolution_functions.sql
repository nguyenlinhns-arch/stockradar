create or replace function public.inspect_stockradar_checkout_approval_v1(p_token_hash text)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  approval_row private.checkout_approvals%rowtype;
  request_row private.checkout_requests%rowtype;
  plan_row private.billing_plans%rowtype;
  customer_email text;
  normalized_hash text := lower(trim(coalesce(p_token_hash, '')));
begin
  select * into approval_row
  from private.checkout_approvals
  where token_hash = normalized_hash
  for update;

  if approval_row.checkout_id is null then
    raise exception 'APPROVAL_TOKEN_INVALID';
  end if;

  if approval_row.status = 'PENDING' and approval_row.expires_at <= now() then
    update private.checkout_approvals
    set status = 'EXPIRED', updated_at = now()
    where checkout_id = approval_row.checkout_id;
    approval_row.status := 'EXPIRED';
  end if;

  select * into request_row from private.checkout_requests where id = approval_row.checkout_id;
  select * into plan_row from private.billing_plans where id = request_row.plan_id;
  select u.email into customer_email from auth.users u where u.id = request_row.user_id;

  return jsonb_build_object(
    'checkout_id', request_row.id,
    'customer_email', customer_email,
    'amount_vnd', request_row.amount_vnd,
    'payment_reference', request_row.payment_reference,
    'plan_code', plan_row.plan_code,
    'duration_days', plan_row.duration_days,
    'checkout_status', request_row.status,
    'approval_status', approval_row.status,
    'approval_expires_at', approval_row.expires_at,
    'sent_at', approval_row.sent_at,
    'decided_at', approval_row.decided_at
  );
end;
$$;

revoke all on function public.inspect_stockradar_checkout_approval_v1(text) from public, anon, authenticated;
grant execute on function public.inspect_stockradar_checkout_approval_v1(text) to service_role;

create or replace function public.resolve_stockradar_checkout_approval_v1(
  p_token_hash text,
  p_decision text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  approval_row private.checkout_approvals%rowtype;
  request_row private.checkout_requests%rowtype;
  result_value jsonb;
  customer_email text;
  normalized_hash text := lower(trim(coalesce(p_token_hash, '')));
  decision_value text := upper(trim(coalesce(p_decision, '')));
begin
  if decision_value not in ('APPROVE', 'REJECT') then
    raise exception 'INVALID_APPROVAL_DECISION';
  end if;

  select * into approval_row
  from private.checkout_approvals
  where token_hash = normalized_hash
  for update;

  if approval_row.checkout_id is null then
    raise exception 'APPROVAL_TOKEN_INVALID';
  end if;

  select * into request_row
  from private.checkout_requests
  where id = approval_row.checkout_id
  for update;

  select u.email into customer_email from auth.users u where u.id = request_row.user_id;

  if approval_row.status in ('APPROVED','REJECTED') then
    return jsonb_build_object(
      'checkout_id', request_row.id,
      'approval_status', approval_row.status,
      'checkout_status', request_row.status,
      'customer_email', customer_email,
      'payment_reference', request_row.payment_reference,
      'amount_vnd', request_row.amount_vnd,
      'idempotent', true
    );
  end if;

  if approval_row.status = 'EXPIRED' or approval_row.expires_at <= now() then
    update private.checkout_approvals
    set status = 'EXPIRED', updated_at = now()
    where checkout_id = approval_row.checkout_id and status = 'PENDING';
    raise exception 'APPROVAL_TOKEN_EXPIRED';
  end if;

  if decision_value = 'APPROVE' then
    if request_row.status = 'PAID' then
      update private.checkout_approvals
      set status = 'APPROVED', decided_at = coalesce(decided_at, now()), updated_at = now()
      where checkout_id = approval_row.checkout_id;
      return jsonb_build_object(
        'checkout_id', request_row.id,
        'approval_status', 'APPROVED',
        'checkout_status', 'PAID',
        'customer_email', customer_email,
        'payment_reference', request_row.payment_reference,
        'amount_vnd', request_row.amount_vnd,
        'idempotent', true
      );
    end if;

    if request_row.status <> 'USER_CONFIRMED' then
      raise exception 'CHECKOUT_NOT_APPROVABLE';
    end if;

    result_value := private.verify_manual_checkout(
      request_row.id,
      'owner-email:' || substr(normalized_hash, 1, 16)
    );

    update private.checkout_approvals
    set status = 'APPROVED', decided_at = now(), updated_at = now()
    where checkout_id = approval_row.checkout_id;

    return coalesce(result_value, '{}'::jsonb) || jsonb_build_object(
      'checkout_id', request_row.id,
      'approval_status', 'APPROVED',
      'checkout_status', 'PAID',
      'customer_email', customer_email,
      'payment_reference', request_row.payment_reference,
      'amount_vnd', request_row.amount_vnd,
      'idempotent', false
    );
  end if;

  if request_row.status = 'USER_CONFIRMED' then
    update private.checkout_requests
    set status = 'CANCELLED', updated_at = now()
    where id = request_row.id;
  end if;

  update private.checkout_approvals
  set status = 'REJECTED', decided_at = now(), updated_at = now()
  where checkout_id = approval_row.checkout_id;

  return jsonb_build_object(
    'checkout_id', request_row.id,
    'approval_status', 'REJECTED',
    'checkout_status', case when request_row.status = 'USER_CONFIRMED' then 'CANCELLED' else request_row.status end,
    'customer_email', customer_email,
    'payment_reference', request_row.payment_reference,
    'amount_vnd', request_row.amount_vnd,
    'idempotent', false
  );
end;
$$;

revoke all on function public.resolve_stockradar_checkout_approval_v1(text, text) from public, anon, authenticated;
grant execute on function public.resolve_stockradar_checkout_approval_v1(text, text) to service_role;
