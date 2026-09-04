-- Defense in depth: private SECURITY DEFINER trigger functions must not retain
-- default EXECUTE privileges for browser or service roles. Trigger execution
-- itself does not require callers to invoke these functions directly.

revoke all on function private.queue_stockradar_premium_activation_from_grant()
  from public, anon, authenticated, service_role;
revoke all on function private.queue_stockradar_premium_activation_from_payment()
  from public, anon, authenticated, service_role;
revoke all on function private.queue_stockradar_welcome_on_email_verified()
  from public, anon, authenticated, service_role;

grant execute on function private.queue_stockradar_premium_activation_from_grant() to postgres;
grant execute on function private.queue_stockradar_premium_activation_from_payment() to postgres;
grant execute on function private.queue_stockradar_welcome_on_email_verified() to postgres;
