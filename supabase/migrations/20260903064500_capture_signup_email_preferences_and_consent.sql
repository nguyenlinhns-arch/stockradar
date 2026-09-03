create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  terms_version text;
  privacy_version text;
  product_email_version text;
  wants_daily_brief boolean := false;
  wants_event_alerts boolean := false;
  wants_product_email boolean := false;
begin
  insert into public.profiles (id, account_tier, account_status)
  values (new.id, 'FREE', case when new.email_confirmed_at is null then 'PENDING' else 'ACTIVE' end)
  on conflict (id) do nothing;

  if coalesce((new.raw_user_meta_data -> 'terms_accepted') = 'true'::jsonb, false) then
    terms_version := nullif(trim(new.raw_user_meta_data ->> 'terms_version'), '');
    if terms_version is not null then
      insert into public.consent_receipts (user_id, purpose, document_version)
      values (new.id, 'TERMS', terms_version)
      on conflict do nothing;
    end if;
  end if;

  if coalesce((new.raw_user_meta_data -> 'privacy_accepted') = 'true'::jsonb, false) then
    privacy_version := nullif(trim(new.raw_user_meta_data ->> 'privacy_version'), '');
    if privacy_version is not null then
      insert into public.consent_receipts (user_id, purpose, document_version)
      values (new.id, 'PRIVACY', privacy_version)
      on conflict do nothing;
    end if;
  end if;

  wants_daily_brief := coalesce((new.raw_user_meta_data -> 'product_email_daily_brief') = 'true'::jsonb, false);
  wants_event_alerts := coalesce((new.raw_user_meta_data -> 'product_email_event_alerts') = 'true'::jsonb, false);
  wants_product_email := coalesce((new.raw_user_meta_data -> 'product_email_consent') = 'true'::jsonb, false)
    and (wants_daily_brief or wants_event_alerts);

  if wants_product_email then
    insert into public.product_email_preferences (
      user_id,
      enabled,
      daily_brief,
      event_alerts,
      post_session_digest,
      weekly_report
    ) values (
      new.id,
      false,
      wants_daily_brief,
      wants_event_alerts,
      false,
      false
    )
    on conflict (user_id) do update set
      enabled = false,
      daily_brief = excluded.daily_brief,
      event_alerts = excluded.event_alerts,
      post_session_digest = false,
      weekly_report = false,
      updated_at = now();

    product_email_version := nullif(trim(new.raw_user_meta_data ->> 'product_email_consent_version'), '');
    if product_email_version is not null then
      insert into public.product_email_consent_events (
        user_id,
        granted,
        document_version,
        source
      ) values (
        new.id,
        true,
        product_email_version,
        'SIGNUP'
      );
    end if;
  end if;

  return new;
end;
$$;
