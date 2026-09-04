create or replace function private.extend_confirmed_checkout_window_v1()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.status = 'USER_CONFIRMED' and old.status is distinct from 'USER_CONFIRMED' then
    new.expires_at := greatest(new.expires_at, now() + interval '24 hours');
  end if;
  return new;
end;
$$;

revoke all on function private.extend_confirmed_checkout_window_v1() from public, anon, authenticated;

drop trigger if exists trg_extend_confirmed_checkout_window_v1 on private.checkout_requests;
create trigger trg_extend_confirmed_checkout_window_v1
before update on private.checkout_requests
for each row execute function private.extend_confirmed_checkout_window_v1();

create or replace function private.notify_checkout_approval_on_confirm_v1()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  config_row private.checkout_approval_config%rowtype;
  request_id bigint;
begin
  if new.status = 'USER_CONFIRMED' and old.status is distinct from 'USER_CONFIRMED' then
    select * into config_row
    from private.checkout_approval_config
    where singleton is true and enabled is true;

    if config_row.singleton is true then
      select net.http_post(
        url := config_row.function_url,
        body := jsonb_build_object('action', 'notify', 'checkout_id', new.id),
        headers := jsonb_build_object(
          'Content-Type', 'application/json',
          'x-stockradar-checkout-hook', config_row.hook_token
        ),
        timeout_milliseconds := 8000
      ) into request_id;
    end if;
  end if;
  return new;
exception when others then
  return new;
end;
$$;

revoke all on function private.notify_checkout_approval_on_confirm_v1() from public, anon, authenticated;

drop trigger if exists trg_notify_checkout_approval_on_confirm_v1 on private.checkout_requests;
create trigger trg_notify_checkout_approval_on_confirm_v1
after update on private.checkout_requests
for each row execute function private.notify_checkout_approval_on_confirm_v1();
