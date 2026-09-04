alter table private.email_subscription_intents
  add column if not exists first_source_path text,
  add column if not exists last_source_path text,
  add column if not exists first_utm_source text,
  add column if not exists last_utm_source text,
  add column if not exists first_utm_campaign text,
  add column if not exists last_utm_campaign text,
  add column if not exists first_referrer_host text,
  add column if not exists last_referrer_host text;

alter table private.email_subscription_intents
  drop constraint if exists email_subscription_intents_source_path_length,
  add constraint email_subscription_intents_source_path_length check (
    (first_source_path is null or char_length(first_source_path) <= 256)
    and (last_source_path is null or char_length(last_source_path) <= 256)
  ),
  drop constraint if exists email_subscription_intents_utm_length,
  add constraint email_subscription_intents_utm_length check (
    (first_utm_source is null or char_length(first_utm_source) <= 120)
    and (last_utm_source is null or char_length(last_utm_source) <= 120)
    and (first_utm_campaign is null or char_length(first_utm_campaign) <= 160)
    and (last_utm_campaign is null or char_length(last_utm_campaign) <= 160)
  ),
  drop constraint if exists email_subscription_intents_referrer_length,
  add constraint email_subscription_intents_referrer_length check (
    (first_referrer_host is null or char_length(first_referrer_host) <= 253)
    and (last_referrer_host is null or char_length(last_referrer_host) <= 253)
  );

create or replace function public.capture_email_subscription_interest_v2(
  p_email text,
  p_daily_brief boolean,
  p_event_alerts boolean,
  p_consent_version text,
  p_ip_hash text,
  p_source_path text,
  p_utm_source text,
  p_utm_campaign text,
  p_referrer_host text
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
  clean_source_path text;
  clean_utm_source text;
  clean_utm_campaign text;
  clean_referrer_host text;
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

  clean_source_path := nullif(left(regexp_replace(btrim(coalesce(p_source_path, '')), '[\r\n\t]', '', 'g'), 256), '');
  if clean_source_path is not null and left(clean_source_path, 1) <> '/' then
    clean_source_path := null;
  end if;
  clean_utm_source := nullif(left(regexp_replace(btrim(coalesce(p_utm_source, '')), '[\r\n\t]', '', 'g'), 120), '');
  clean_utm_campaign := nullif(left(regexp_replace(btrim(coalesce(p_utm_campaign, '')), '[\r\n\t]', '', 'g'), 160), '');
  clean_referrer_host := nullif(lower(left(regexp_replace(btrim(coalesce(p_referrer_host, '')), '[^a-zA-Z0-9.:-]', '', 'g'), 253)), '');

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
    last_ip_hash,
    first_source_path,
    last_source_path,
    first_utm_source,
    last_utm_source,
    first_utm_campaign,
    last_utm_campaign,
    first_referrer_host,
    last_referrer_host
  ) values (
    normalized_email,
    coalesce(p_daily_brief, false),
    coalesce(p_event_alerts, false),
    p_consent_version,
    'PENDING_VERIFICATION',
    'WEBSITE_PREAUTH',
    p_ip_hash,
    clean_source_path,
    clean_source_path,
    clean_utm_source,
    clean_utm_source,
    clean_utm_campaign,
    clean_utm_campaign,
    clean_referrer_host,
    clean_referrer_host
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
    last_ip_hash = excluded.last_ip_hash,
    first_source_path = coalesce(private.email_subscription_intents.first_source_path, excluded.first_source_path),
    last_source_path = coalesce(excluded.last_source_path, private.email_subscription_intents.last_source_path),
    first_utm_source = coalesce(private.email_subscription_intents.first_utm_source, excluded.first_utm_source),
    last_utm_source = coalesce(excluded.last_utm_source, private.email_subscription_intents.last_utm_source),
    first_utm_campaign = coalesce(private.email_subscription_intents.first_utm_campaign, excluded.first_utm_campaign),
    last_utm_campaign = coalesce(excluded.last_utm_campaign, private.email_subscription_intents.last_utm_campaign),
    first_referrer_host = coalesce(private.email_subscription_intents.first_referrer_host, excluded.first_referrer_host),
    last_referrer_host = coalesce(excluded.last_referrer_host, private.email_subscription_intents.last_referrer_host);

  return jsonb_build_object('accepted', true, 'status', 'PENDING_VERIFICATION');
end;
$$;

revoke all on function public.capture_email_subscription_interest_v2(text,boolean,boolean,text,text,text,text,text,text) from public, anon, authenticated;
grant execute on function public.capture_email_subscription_interest_v2(text,boolean,boolean,text,text,text,text,text,text) to service_role;

comment on function public.capture_email_subscription_interest_v2(text,boolean,boolean,text,text,text,text,text,text) is
  'Service-role-only pre-auth email-interest capture with minimal first/last-touch source attribution. Never authorizes delivery.';
