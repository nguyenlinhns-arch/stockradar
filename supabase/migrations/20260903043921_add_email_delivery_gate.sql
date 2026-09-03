create table private.email_delivery_gate (
  singleton boolean primary key default true check (singleton),
  provider_name text,
  provider_configured boolean not null default false,
  sender_domain_verified boolean not null default false,
  unsubscribe_ready boolean not null default false,
  bounce_complaint_ready boolean not null default false,
  compliance_approved boolean not null default false,
  current_consent_version text not null default '2026-09-03',
  sending_enabled boolean not null default false,
  updated_at timestamptz not null default now(),
  evidence_ref text,
  constraint email_delivery_gate_safe_enable check (
    not sending_enabled or (
      provider_configured
      and sender_domain_verified
      and unsubscribe_ready
      and bounce_complaint_ready
      and compliance_approved
      and length(trim(current_consent_version)) > 0
      and length(trim(coalesce(evidence_ref, ''))) > 0
    )
  )
);

insert into private.email_delivery_gate (singleton)
values (true)
on conflict (singleton) do nothing;

alter table private.email_delivery_gate enable row level security;
revoke all on table private.email_delivery_gate from public, anon, authenticated;

create view private.product_email_eligibility
with (security_invoker = true)
as
select
  pref.user_id,
  pref.enabled as preference_enabled,
  pref.daily_brief,
  pref.event_alerts,
  pref.post_session_digest,
  pref.weekly_report,
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
    and prof.account_tier in ('TRIAL','PAID')
    and coalesce(consent.granted, false)
    and consent.document_version = gate.current_consent_version
    and suppression.user_id is null
    and gate.sending_enabled
  ) as eligible_to_send
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
  on suppression.user_id = pref.user_id
 and suppression.lifted_at is null;

revoke all on private.product_email_eligibility from public, anon, authenticated;
