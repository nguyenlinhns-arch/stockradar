-- StockRadar email entitlement: Free gets the 09:00 daily brief; Premium gets intraday action alerts.
-- Delivery still requires verified email, current consent, no suppression and the fail-closed delivery gate.

create or replace function public.enforce_stockradar_product_email_entitlement()
returns trigger
language plpgsql
set search_path = ''
as $$
declare
  tier text;
  status text;
begin
  if not new.enabled then
    return new;
  end if;

  select p.account_tier, p.account_status
    into tier, status
  from public.profiles p
  where p.id = new.user_id;

  if status <> 'ACTIVE' then
    raise exception 'product email requires active account';
  end if;

  if tier not in ('FREE','TRIAL','PAID') then
    raise exception 'product email requires eligible account tier';
  end if;

  if tier = 'FREE' and not coalesce(new.daily_brief, false) then
    raise exception 'Free product email requires daily brief';
  end if;

  if tier in ('TRIAL','PAID') and not (
    coalesce(new.daily_brief, false)
    or coalesce(new.event_alerts, false)
    or coalesce(new.post_session_digest, false)
    or coalesce(new.weekly_report, false)
  ) then
    raise exception 'Premium product email requires at least one selected product';
  end if;

  return new;
end;
$$;

create or replace function private.disable_stockradar_product_email_on_ineligible_profile()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.account_status <> 'ACTIVE' or new.account_tier not in ('FREE','TRIAL','PAID') then
    update public.product_email_preferences
       set enabled = false,
           updated_at = now()
     where user_id = new.id and enabled is true;
  elsif new.account_tier = 'FREE' then
    update public.product_email_preferences
       set enabled = false,
           updated_at = now()
     where user_id = new.id
       and enabled is true
       and coalesce(daily_brief, false) is not true;
  end if;
  return new;
end;
$$;

create or replace function public.handle_email_verified()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if old.email_confirmed_at is null and new.email_confirmed_at is not null then
    update public.profiles
       set account_status = 'ACTIVE', updated_at = now()
     where id = new.id and account_status = 'PENDING';

    update public.product_email_preferences pref
       set enabled = true,
           updated_at = now()
     where pref.user_id = new.id
       and exists (
         select 1
         from public.profiles prof
         where prof.id = new.id
           and prof.account_status = 'ACTIVE'
           and (
             (prof.account_tier = 'FREE' and pref.daily_brief is true)
             or (
               prof.account_tier in ('TRIAL','PAID')
               and (
                 pref.daily_brief is true
                 or pref.event_alerts is true
                 or pref.post_session_digest is true
                 or pref.weekly_report is true
               )
             )
           )
       )
       and exists (
         select 1
         from public.product_email_consent_events event
         cross join private.email_delivery_gate gate
         where event.user_id = new.id
           and event.id = (
             select latest.id
             from public.product_email_consent_events latest
             where latest.user_id = new.id
             order by latest.recorded_at desc, latest.id desc
             limit 1
           )
           and event.granted is true
           and event.document_version = gate.current_consent_version
       );
  end if;
  return new;
end;
$$;

create or replace view private.product_email_eligibility
with (security_invoker = true)
as
select
  pref.user_id,
  pref.enabled as preference_enabled,
  (pref.daily_brief and prof.account_tier in ('FREE','TRIAL','PAID')) as daily_brief,
  (pref.event_alerts and prof.account_tier in ('TRIAL','PAID')) as event_alerts,
  (pref.post_session_digest and prof.account_tier in ('TRIAL','PAID')) as post_session_digest,
  (pref.weekly_report and prof.account_tier in ('TRIAL','PAID')) as weekly_report,
  prof.account_tier,
  prof.account_status,
  consent.granted as latest_consent_granted,
  consent.document_version as latest_consent_version,
  consent.recorded_at as latest_consent_at,
  suppression.reason as suppression_reason,
  gate.sending_enabled,
  (
    pref.enabled
    and prof.account_status = 'ACTIVE'
    and prof.account_tier in ('FREE','TRIAL','PAID')
    and coalesce(consent.granted, false)
    and consent.document_version = gate.current_consent_version
    and suppression.user_id is null
    and gate.sending_enabled
    and (
      pref.daily_brief
      or (
        prof.account_tier in ('TRIAL','PAID')
        and (pref.event_alerts or pref.post_session_digest or pref.weekly_report)
      )
    )
  ) as eligible_to_send,
  case
    when pref.daily_brief and prof.account_tier in ('TRIAL','PAID') then 'PREMIUM'
    when pref.daily_brief and prof.account_tier = 'FREE' then 'FREE'
    else 'NONE'
  end as daily_brief_content_tier,
  (
    pref.enabled
    and prof.account_status = 'ACTIVE'
    and prof.account_tier in ('TRIAL','PAID')
    and coalesce(consent.granted, false)
    and consent.document_version = gate.current_consent_version
    and suppression.user_id is null
    and gate.sending_enabled
  ) as eligible_for_premium
from public.product_email_preferences pref
join public.profiles prof on prof.id = pref.user_id
cross join private.email_delivery_gate gate
left join lateral (
  select event.granted, event.document_version, event.recorded_at
  from public.product_email_consent_events event
  where event.user_id = pref.user_id
  order by event.recorded_at desc, event.id desc
  limit 1
) consent on true
left join private.email_suppressions suppression
  on suppression.user_id = pref.user_id and suppression.lifted_at is null;
