-- Privacy policy 2026-09-04 adds authenticated API operational telemetry
-- disclosure and clarifies account deletion/billing-history retention.
-- Product-email delivery remains fail-closed and requires consent to the
-- current document version.

update private.email_delivery_gate
set current_consent_version = '2026-09-04',
    updated_at = now()
where singleton is true;

update public.product_email_preferences pref
set enabled = false,
    updated_at = now()
where pref.enabled is true
  and not exists (
    select 1
    from public.product_email_consent_events event
    where event.user_id = pref.user_id
      and event.granted is true
      and event.document_version = '2026-09-04'
  );
