create or replace function private.dispatch_stockradar_admin_signup_worker_v1()
returns jsonb
language plpgsql
security definer
set search_path to ''
as $$
declare
  v_config private.checkout_approval_config%rowtype;
  v_function_url text;
  v_request_id bigint;
  v_due boolean := false;
begin
  select * into v_config
    from private.checkout_approval_config c
   where c.singleton is true
     and c.enabled is true;

  if v_config.singleton is null then
    return jsonb_build_object('status','ADMIN_NOTIFICATION_NOT_CONFIGURED');
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

  v_function_url := regexp_replace(v_config.function_url, '/checkout-approval/?$', '/free-signup-admin-notify');
  if v_function_url = v_config.function_url then
    return jsonb_build_object('status','ADMIN_NOTIFICATION_URL_INVALID');
  end if;

  select net.http_post(
    url := v_function_url,
    headers := jsonb_build_object(
      'Content-Type','application/json',
      'x-stockradar-checkout-hook',v_config.hook_token
    ),
    body := jsonb_build_object('limit',20),
    timeout_milliseconds := 8000
  ) into v_request_id;

  return jsonb_build_object('status','DISPATCHED','request_id',v_request_id);
exception when others then
  return jsonb_build_object('status','DISPATCH_FAILED');
end;
$$;

revoke all on function private.dispatch_stockradar_admin_signup_worker_v1() from public, anon, authenticated;
