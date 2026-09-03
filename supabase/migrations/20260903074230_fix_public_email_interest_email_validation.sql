create or replace function public.capture_email_subscription_interest(
  p_email text,
  p_daily_brief boolean,
  p_event_alerts boolean,
  p_consent_version text,
  p_ip_hash text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  normalized_email text;
  active_consent_version text;
  recent_attempts integer;
begin
  normalized_email := lower(btrim(coalesce(p_email, '')));

  if char_length(normalized_email) < 3
     or char_length(normalized_email) > 160
     or normalized_email !~ '^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$' then
    raise exception 'invalid email';
  end if;

  if not coalesce(p_daily_brief, false) and not coalesce(p_event_alerts, false) then
    raise exception 'select at least one email type';
  end if;

  if p_ip_hash is null or char_length(p_ip_hash) < 16 or char_length(p_ip_hash) > 128 then
    raise exception 'invalid request fingerprint';
  end if;

  select gate.current_consent_version
    into active_consent_version
  from private.email_delivery_gate gate
  where gate.singleton = true;

  if active_consent_version is null or p_consent_version is distinct from active_consent_version then
    raise exception 'consent version mismatch';
  end if;

  delete from private.email_subscription_rate_events
   where occurred_at < now() - interval '24 hours';

  select count(*)::integer
    into recent_attempts
  from private.email_subscription_rate_events
  where ip_hash = p_ip_hash
    and occurred_at >= now() - interval '1 hour';

  if recent_attempts >= 10 then
    raise exception 'rate limit exceeded';
  end if;

  insert into private.email_subscription_rate_events (ip_hash)
  values (p_ip_hash);

  delete from private.email_subscription_intents
   where status = 'PENDING_VERIFICATION'
     and expires_at < now();

  insert into private.email_subscription_intents (
    email,
    daily_brief,
    event_alerts,
    consent_version,
    status,
    source,
    last_ip_hash
  ) values (
    normalized_email,
    coalesce(p_daily_brief, false),
    coalesce(p_event_alerts, false),
    p_consent_version,
    'PENDING_VERIFICATION',
    'WEBSITE_PREAUTH',
    p_ip_hash
  )
  on conflict (email) do update set
    daily_brief = excluded.daily_brief,
    event_alerts = excluded.event_alerts,
    consent_version = excluded.consent_version,
    status = case
      when private.email_subscription_intents.status in ('VERIFIED','BLOCKED')
        then private.email_subscription_intents.status
      else 'PENDING_VERIFICATION'
    end,
    last_seen_at = now(),
    expires_at = case
      when private.email_subscription_intents.status = 'VERIFIED'
        then private.email_subscription_intents.expires_at
      else now() + interval '30 days'
    end,
    request_count = private.email_subscription_intents.request_count + 1,
    last_ip_hash = excluded.last_ip_hash;

  return jsonb_build_object('accepted', true, 'status', 'PENDING_VERIFICATION');
end;
$$;

revoke all on function public.capture_email_subscription_interest(text,boolean,boolean,text,text) from public, anon, authenticated;
grant execute on function public.capture_email_subscription_interest(text,boolean,boolean,text,text) to service_role;
