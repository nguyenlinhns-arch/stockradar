create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

create table public.product_email_preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  enabled boolean not null default false,
  daily_brief boolean not null default true,
  event_alerts boolean not null default true,
  post_session_digest boolean not null default true,
  weekly_report boolean not null default true,
  updated_at timestamptz not null default now()
);

create table public.product_email_consent_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  granted boolean not null,
  document_version text not null check (length(trim(document_version)) between 1 and 64),
  source text not null default 'ACCOUNT_CENTER' check (source in ('ACCOUNT_CENTER','SIGNUP','SUPPORT')),
  recorded_at timestamptz not null default now()
);

create index product_email_consent_by_user
  on public.product_email_consent_events(user_id, recorded_at desc);

create table private.email_outbox (
  id uuid primary key default gen_random_uuid(),
  idempotency_key text not null unique,
  user_id uuid not null references auth.users(id) on delete cascade,
  email_kind text not null check (email_kind in ('DAILY_BRIEF','EVENT_ALERT','POST_SESSION_DIGEST','WEEKLY_REPORT')),
  snapshot_id text,
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'PENDING' check (status in ('PENDING','PROCESSING','SENT','SUPPRESSED','FAILED')),
  scheduled_at timestamptz not null default now(),
  attempts integer not null default 0 check (attempts >= 0),
  provider_message_id text,
  last_error text,
  created_at timestamptz not null default now(),
  sent_at timestamptz
);

create index email_outbox_pending
  on private.email_outbox(status, scheduled_at)
  where status in ('PENDING','FAILED');

create table private.email_suppressions (
  user_id uuid primary key references auth.users(id) on delete cascade,
  reason text not null check (reason in ('UNSUBSCRIBE','BOUNCE','COMPLAINT','SECURITY','ADMIN')),
  source_ref text,
  created_at timestamptz not null default now(),
  lifted_at timestamptz
);

alter table public.product_email_preferences enable row level security;
alter table public.product_email_consent_events enable row level security;
alter table private.email_outbox enable row level security;
alter table private.email_suppressions enable row level security;

create policy "users can read own product email preferences"
on public.product_email_preferences
for select
to authenticated
using ((select auth.uid()) = user_id);

create policy "users can insert own product email preferences"
on public.product_email_preferences
for insert
to authenticated
with check ((select auth.uid()) = user_id);

create policy "users can update own product email preferences"
on public.product_email_preferences
for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy "users can read own product email consent events"
on public.product_email_consent_events
for select
to authenticated
using ((select auth.uid()) = user_id);

create policy "users can append own product email consent events"
on public.product_email_consent_events
for insert
to authenticated
with check ((select auth.uid()) = user_id);

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

  if status <> 'ACTIVE' or tier not in ('TRIAL','PAID') then
    raise exception 'product email requires active TRIAL or PAID account';
  end if;

  return new;
end;
$$;

create trigger product_email_preferences_enforce_entitlement
before insert or update on public.product_email_preferences
for each row execute function public.enforce_stockradar_product_email_entitlement();

create trigger product_email_preferences_set_updated_at
before update on public.product_email_preferences
for each row execute function public.set_stockradar_updated_at();

create or replace function public.disable_stockradar_product_email_on_ineligible_profile()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.account_status <> 'ACTIVE' or new.account_tier = 'FREE' then
    update public.product_email_preferences
      set enabled = false
    where user_id = new.id and enabled is true;
  end if;
  return new;
end;
$$;

revoke all on function public.disable_stockradar_product_email_on_ineligible_profile() from public, anon, authenticated;

create trigger profiles_disable_ineligible_product_email
after update of account_tier, account_status on public.profiles
for each row execute function public.disable_stockradar_product_email_on_ineligible_profile();

revoke all on table public.product_email_preferences from anon, authenticated;
revoke all on table public.product_email_consent_events from anon, authenticated;
grant select, insert, update on table public.product_email_preferences to authenticated;
grant select, insert on table public.product_email_consent_events to authenticated;

revoke all on table private.email_outbox from public, anon, authenticated;
revoke all on table private.email_suppressions from public, anon, authenticated;
