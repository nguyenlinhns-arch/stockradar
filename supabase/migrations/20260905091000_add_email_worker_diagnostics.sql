-- Authentication for a read-only worker configuration check, even before delivery
-- activation. This grants no ability to claim or send outbox messages.
create or replace function public.verify_stockradar_email_diagnostic_token_v1(p_token_hash text)
returns boolean language sql security definer set search_path = '' as $$
  select coalesce((select scheduler_configured and token_hash=lower(trim(coalesce(p_token_hash,'')))
    from private.email_worker_scheduler_gate where singleton),false);
$$;
revoke all on function public.verify_stockradar_email_diagnostic_token_v1(text) from public,anon,authenticated;
grant execute on function public.verify_stockradar_email_diagnostic_token_v1(text) to service_role;
