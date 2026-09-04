do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema='public' and table_name='watchlist_items' and column_name='average_cost'
  ) and not exists (
    select 1 from information_schema.columns
    where table_schema='public' and table_name='watchlist_items' and column_name='cost_basis'
  ) then
    alter table public.watchlist_items rename column average_cost to cost_basis;
  end if;
end $$;

alter table public.watchlist_items drop constraint if exists watchlist_items_average_cost_check;
alter table public.watchlist_items drop constraint if exists watchlist_items_cost_basis_check;
alter table public.watchlist_items add constraint watchlist_items_cost_basis_check
  check (cost_basis is null or cost_basis > 0);

comment on column public.watchlist_items.cost_basis is 'Optional user-supplied cost basis for private AI position context; never public.';
