create or replace function public.get_stockradar_resend_webhook_secret_v1()
returns text
language sql
security definer
set search_path = ''
as $$
  select ds.decrypted_secret
  from vault.decrypted_secrets ds
  where ds.name = 'stockradar_resend_webhook_secret'
  order by ds.updated_at desc
  limit 1
$$;

revoke all on function public.get_stockradar_resend_webhook_secret_v1() from public, anon, authenticated;
grant execute on function public.get_stockradar_resend_webhook_secret_v1() to service_role;
