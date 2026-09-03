create table public.user_preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  preferred_horizons text[] not null default '{}'::text[],
  preferred_sectors text[] not null default '{}'::text[],
  updated_at timestamptz not null default now(),
  constraint user_preferences_horizons_allowed check (
    preferred_horizons <@ array['SHORT_TERM','MEDIUM_TERM','LONG_TERM','ACCUMULATION']::text[]
    and cardinality(preferred_horizons) <= 4
  ),
  constraint user_preferences_sector_limit check (cardinality(preferred_sectors) <= 3)
);

create table public.watchlist_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  ticker text not null,
  horizon text not null,
  owns_stock boolean not null default false,
  alert_enabled boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  removed_at timestamptz,
  constraint watchlist_ticker_format check (ticker ~ '^[A-Z]{3}$'),
  constraint watchlist_horizon_allowed check (
    horizon = any (array['SHORT_TERM','MEDIUM_TERM','LONG_TERM','ACCUMULATION']::text[])
  )
);

create unique index watchlist_one_active_ticker_horizon
  on public.watchlist_items(user_id, ticker, horizon)
  where removed_at is null;

create index watchlist_active_by_user
  on public.watchlist_items(user_id, created_at desc)
  where removed_at is null;

create or replace function public.set_stockradar_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

create trigger user_preferences_set_updated_at
before update on public.user_preferences
for each row execute function public.set_stockradar_updated_at();

create trigger watchlist_items_set_updated_at
before update on public.watchlist_items
for each row execute function public.set_stockradar_updated_at();

create or replace function public.enforce_stockradar_watchlist_limit()
returns trigger
language plpgsql
set search_path = ''
as $$
declare
  tier text;
  status text;
  active_count integer;
  max_items integer;
  activating boolean;
begin
  if tg_op = 'UPDATE' and old.user_id <> new.user_id then
    raise exception 'watchlist owner cannot be changed';
  end if;

  activating := new.removed_at is null and (tg_op = 'INSERT' or old.removed_at is not null);
  if not activating then
    return new;
  end if;

  perform pg_advisory_xact_lock(hashtextextended(new.user_id::text, 0));

  select p.account_tier, p.account_status
    into tier, status
  from public.profiles p
  where p.id = new.user_id;

  if tier is null or status is null then
    raise exception 'active StockRadar profile required';
  end if;
  if status <> 'ACTIVE' then
    raise exception 'verified active StockRadar account required';
  end if;

  max_items := case when tier = 'PAID' then 20 else 3 end;

  select count(*)
    into active_count
  from public.watchlist_items w
  where w.user_id = new.user_id
    and w.removed_at is null;

  if active_count >= max_items then
    raise exception 'watchlist limit reached for tier %', tier;
  end if;

  if tier = 'FREE' and new.alert_enabled then
    raise exception 'product alerts are unavailable on FREE tier';
  end if;

  return new;
end;
$$;

create trigger watchlist_items_enforce_limit
before insert or update on public.watchlist_items
for each row execute function public.enforce_stockradar_watchlist_limit();

alter table public.user_preferences enable row level security;
alter table public.watchlist_items enable row level security;

create policy "users can read own preferences"
on public.user_preferences
for select
to authenticated
using ((select auth.uid()) = user_id);

create policy "users can insert own preferences"
on public.user_preferences
for insert
to authenticated
with check ((select auth.uid()) = user_id);

create policy "users can update own preferences"
on public.user_preferences
for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy "users can read own watchlist"
on public.watchlist_items
for select
to authenticated
using ((select auth.uid()) = user_id);

create policy "users can insert own watchlist"
on public.watchlist_items
for insert
to authenticated
with check ((select auth.uid()) = user_id);

create policy "users can update own watchlist"
on public.watchlist_items
for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy "users can delete own watchlist"
on public.watchlist_items
for delete
to authenticated
using ((select auth.uid()) = user_id);

revoke all on table public.user_preferences from anon, authenticated;
revoke all on table public.watchlist_items from anon, authenticated;
grant select, insert, update on table public.user_preferences to authenticated;
grant select, insert, update, delete on table public.watchlist_items to authenticated;
