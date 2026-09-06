-- Freeze approval email contents across idempotent provider retries; never grant on GET.
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
  elsif approval_row.status = 'PENDING' and approval_row.sent_at is null
      and approval_row.expires_at > now() and approval_row.send_attempts < 4 then
    update private.checkout_approvals
    set token_hash = normalized_hash,
        expires_at = approval_row.expires_at,
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
    'confirmed_at', request_row.confirmed_at,
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

-- Retry only existing real submitted requests. No payment/entitlement writes here.
create or replace function private.retry_stockradar_checkout_notifications_v1()
returns jsonb language plpgsql security definer set search_path = '' as $$
declare c private.checkout_approval_config%rowtype; r record; dispatched integer:=0;
begin
  select * into c from private.checkout_approval_config where singleton and enabled;
  if c.singleton is not true then return jsonb_build_object('status','DISABLED'); end if;
  for r in
    select q.id from private.checkout_requests q
    left join private.checkout_approvals a on a.checkout_id=q.id
    where q.status='USER_CONFIRMED' and q.expires_at>now()
      and q.confirmed_at<now()-interval '5 minutes'
      and (a.checkout_id is null or (a.status='PENDING' and a.sent_at is null
        and a.send_attempts<4 and a.expires_at>now() and a.updated_at<now()-interval '5 minutes'))
    order by q.confirmed_at limit 5
  loop
    perform net.http_post(url:=c.function_url,
      headers:=jsonb_build_object('Content-Type','application/json','x-stockradar-checkout-hook',c.hook_token),
      body:=jsonb_build_object('action','notify','checkout_id',r.id), timeout_milliseconds:=8000);
    dispatched:=dispatched+1;
  end loop;
  return jsonb_build_object('status','CHECKED','dispatched',dispatched);
end $$;
revoke all on function private.retry_stockradar_checkout_notifications_v1() from public,anon,authenticated;

do $$ begin
  if exists(select 1 from cron.job where jobname='stockradar-checkout-notification-retry-v1') then
    perform cron.unschedule('stockradar-checkout-notification-retry-v1');
  end if;
  perform cron.schedule('stockradar-checkout-notification-retry-v1','*/5 * * * *',
    $cron$select private.retry_stockradar_checkout_notifications_v1();$cron$);
end $$;
