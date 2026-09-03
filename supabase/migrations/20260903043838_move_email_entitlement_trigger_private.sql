drop trigger if exists profiles_disable_ineligible_product_email on public.profiles;

drop function if exists public.disable_stockradar_product_email_on_ineligible_profile();

create or replace function private.disable_stockradar_product_email_on_ineligible_profile()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.account_status <> 'ACTIVE' or new.account_tier = 'FREE' then
    update public.product_email_preferences
      set enabled = false
    where user_id = new.id and enabled is true;
  end if;
  return new;
end;
$$;

revoke all on function private.disable_stockradar_product_email_on_ineligible_profile() from public, anon, authenticated;

create trigger profiles_disable_ineligible_product_email
after update of account_tier, account_status on public.profiles
for each row execute function private.disable_stockradar_product_email_on_ineligible_profile();
