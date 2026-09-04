alter table private.email_outbox
  drop constraint if exists email_outbox_email_kind_check;

alter table private.email_outbox
  add constraint email_outbox_email_kind_check
  check (email_kind = any (array[
    'DAILY_BRIEF'::text,
    'EVENT_ALERT'::text,
    'POST_SESSION_DIGEST'::text,
    'WEEKLY_REPORT'::text,
    'WELCOME_FREE'::text,
    'WELCOME_PREMIUM_PENDING'::text,
    'WELCOME_PREMIUM_ACTIVE'::text
  ]));

create or replace function private.queue_stockradar_welcome_on_email_verified()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  selected_plan text;
  welcome_kind text;
  welcome_tier text;
begin
  if old.email_confirmed_at is null and new.email_confirmed_at is not null then
    selected_plan := lower(coalesce(nullif(trim(new.raw_user_meta_data ->> 'selected_plan_interest'), ''), 'free'));

    if selected_plan = 'premium' then
      welcome_kind := 'WELCOME_PREMIUM_PENDING';
      welcome_tier := 'PREMIUM_PENDING';
    else
      welcome_kind := 'WELCOME_FREE';
      welcome_tier := 'FREE';
    end if;

    insert into private.email_outbox (
      idempotency_key,
      user_id,
      email_kind,
      payload,
      status,
      scheduled_at
    ) values (
      'welcome-verified:' || new.id::text,
      new.id,
      welcome_kind,
      jsonb_build_object(
        'template_key', lower(welcome_kind),
        'transactional', true,
        'account_tier', welcome_tier,
        'selected_plan_interest', selected_plan,
        'email_verified_at', new.email_confirmed_at,
        'recipient_email', new.email,
        'message_policy', case
          when selected_plan = 'premium' then 'Premium was selected at signup; payment must be verified before Premium activation.'
          else 'Free account verified; no Premium action alerts are included.'
        end
      ),
      'PENDING',
      now()
    )
    on conflict (idempotency_key) do nothing;
  end if;

  return new;
end;
$$;

drop trigger if exists zz_stockradar_queue_welcome_email_verified on auth.users;
create trigger zz_stockradar_queue_welcome_email_verified
after update of email_confirmed_at on auth.users
for each row
execute function private.queue_stockradar_welcome_on_email_verified();

create or replace function private.queue_stockradar_premium_activation_from_grant()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.revoked_at is null
     and new.starts_at <= now()
     and new.ends_at > now()
     and exists (
       select 1
       from private.payment_events p
       where p.id = new.payment_event_id
         and p.user_id = new.user_id
         and p.status = 'PAID'
         and p.verified_at is not null
     ) then
    insert into private.email_outbox (
      idempotency_key,
      user_id,
      email_kind,
      payload,
      status,
      scheduled_at
    ) values (
      'welcome-premium-active:' || new.payment_event_id::text,
      new.user_id,
      'WELCOME_PREMIUM_ACTIVE',
      jsonb_build_object(
        'template_key', 'welcome_premium_active',
        'transactional', true,
        'account_tier', 'PAID',
        'payment_event_id', new.payment_event_id,
        'premium_starts_at', new.starts_at,
        'premium_ends_at', new.ends_at,
        'granted_days', new.granted_days,
        'message_policy', 'Premium access is active only because a PAID payment event has been verified.'
      ),
      'PENDING',
      now()
    )
    on conflict (idempotency_key) do nothing;
  end if;

  return new;
end;
$$;

drop trigger if exists zz_stockradar_queue_premium_activation_grant on private.subscription_grants;
create trigger zz_stockradar_queue_premium_activation_grant
after insert or update of starts_at, ends_at, revoked_at on private.subscription_grants
for each row
execute function private.queue_stockradar_premium_activation_from_grant();

create or replace function private.queue_stockradar_premium_activation_from_payment()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  grant_row record;
begin
  if new.status = 'PAID' and new.verified_at is not null then
    for grant_row in
      select g.*
      from private.subscription_grants g
      where g.payment_event_id = new.id
        and g.user_id = new.user_id
        and g.revoked_at is null
        and g.starts_at <= now()
        and g.ends_at > now()
    loop
      insert into private.email_outbox (
        idempotency_key,
        user_id,
        email_kind,
        payload,
        status,
        scheduled_at
      ) values (
        'welcome-premium-active:' || new.id::text,
        new.user_id,
        'WELCOME_PREMIUM_ACTIVE',
        jsonb_build_object(
          'template_key', 'welcome_premium_active',
          'transactional', true,
          'account_tier', 'PAID',
          'payment_event_id', new.id,
          'premium_starts_at', grant_row.starts_at,
          'premium_ends_at', grant_row.ends_at,
          'granted_days', grant_row.granted_days,
          'message_policy', 'Premium access is active only because a PAID payment event has been verified.'
        ),
        'PENDING',
        now()
      )
      on conflict (idempotency_key) do nothing;
    end loop;
  end if;

  return new;
end;
$$;

drop trigger if exists zz_stockradar_queue_premium_activation_payment on private.payment_events;
create trigger zz_stockradar_queue_premium_activation_payment
after insert or update of status, verified_at on private.payment_events
for each row
execute function private.queue_stockradar_premium_activation_from_payment();
