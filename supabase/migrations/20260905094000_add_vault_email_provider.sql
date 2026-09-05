-- Sending credentials remain in Vault; the worker is the only client of this RPC.
create or replace function public.get_stockradar_email_provider_config_v1()
returns jsonb language sql security definer set search_path = '' as $$
  select jsonb_build_object('api_key',(select decrypted_secret from vault.decrypted_secrets
    where name='stockradar_resend_sending_key' order by created_at desc limit 1),
    'from_address','StockRadar <alerts@stockradar.vn>');
$$;
revoke all on function public.get_stockradar_email_provider_config_v1() from public,anon,authenticated;
grant execute on function public.get_stockradar_email_provider_config_v1() to service_role;
